# test MDs with static certificates
import json
import os

import pytest

from md_conf import HttpdConf
from md_env import MDTestEnv


@pytest.mark.skipif(condition=not MDTestEnv.has_acme_server(),
                    reason="no ACME test server configured")
class TestStatic:

    @pytest.fixture(autouse=True, scope='class')
    def _class_scope(self, env):
        env.APACHE_CONF_SRC = "data/test_auto"
        env.check_acme()
        env.clear_store()
        HttpdConf(env).install()
        assert env.apache_restart() == 0

    @pytest.fixture(autouse=True, scope='function')
    def _method_scope(self, env, request):
        env.clear_store()
        self.test_domain = env.get_request_domain(request)

    def test_730_001(self, env):
        # MD with static cert files, will not be driven
        domain = self.test_domain
        domains = [domain, 'www.%s' % domain]
        testpath = os.path.join(env.gen_dir, 'test_920_001')
        # cert that is only 10 more days valid
        env.create_self_signed_cert(domains, {"notBefore": -80, "notAfter": 10},
                                    serial=730001, path=testpath)
        cert_file = os.path.join(testpath, 'pubcert.pem')
        pkey_file = os.path.join(testpath, 'privkey.pem')
        assert os.path.exists(cert_file)
        assert os.path.exists(pkey_file)
        conf = HttpdConf(env)
        conf.add_admin("admin@not-forbidden.org")
        conf.start_md(domains)
        conf.add(f"MDCertificateFile {cert_file}")
        conf.add(f"MDCertificateKeyFile {pkey_file}")
        conf.end_md()
        conf.add_vhost(domain)
        conf.install()
        assert env.apache_restart() == 0
        
        # check if the domain uses it, it appears in our stats and renewal is off
        cert = env.get_cert(domain)
        assert cert.same_serial_as(730001)
        stat = env.get_md_status(domain)
        assert stat
        assert 'cert' in stat
        assert stat['renew'] is True
        assert 'renewal' not in stat

    def test_730_002(self, env):
        # MD with static cert files, force driving
        domain = self.test_domain
        domains = [domain, 'www.%s' % domain]
        testpath = os.path.join(env.gen_dir, 'test_920_001')
        # cert that is only 10 more days valid
        env.create_self_signed_cert(domains, {"notBefore": -80, "notAfter": 10},
                                    serial=730001, path=testpath)
        cert_file = os.path.join(testpath, 'pubcert.pem')
        pkey_file = os.path.join(testpath, 'privkey.pem')
        assert os.path.exists(cert_file)
        assert os.path.exists(pkey_file)
        conf = HttpdConf(env)
        conf.add_admin("admin@not-forbidden.org")
        conf.start_md(domains)
        conf.add(f"MDPrivateKeys secp384r1 rsa3072")
        conf.add(f"MDCertificateFile {cert_file}")
        conf.add(f"MDCertificateKeyFile {pkey_file}")
        conf.add("MDRenewMode always")
        conf.end_md()
        conf.add_vhost(domain)
        conf.install()
        assert env.apache_restart() == 0
        
        # check if the domain uses it, it appears in our stats and renewal is on
        cert = env.get_cert(domain)
        assert cert.same_serial_as(730001)
        stat = env.get_md_status(domain)
        assert stat
        assert 'cert' in stat
        assert stat['renew'] is True
        assert env.await_renewal(domains)
        stat = env.get_md_status(domain)
        assert 'renewal' in stat
        assert 'cert' in stat['renewal']
        assert 'rsa' in stat['renewal']['cert']
        assert 'secp384r1' in stat['renewal']['cert']

    def test_730_003(self, env):
        # just configuring one file will not work
        domain = self.test_domain
        domains = [domain, 'www.%s' % domain]
        testpath = os.path.join(env.gen_dir, 'test_920_001')
        # cert that is only 10 more days valid
        env.create_self_signed_cert(domains, {"notBefore": -80, "notAfter": 10},
                                    serial=730001, path=testpath)
        cert_file = os.path.join(testpath, 'pubcert.pem')
        pkey_file = os.path.join(testpath, 'privkey.pem')
        assert os.path.exists(cert_file)
        assert os.path.exists(pkey_file)
        
        conf = HttpdConf(env)
        conf.add_admin("admin@not-forbidden.org")
        conf.start_md(domains)
        conf.add(f"MDCertificateFile {cert_file}")
        conf.end_md()
        conf.add_vhost(domain)
        conf.install()
        assert env.apache_fail() == 0
        
        conf = HttpdConf(env)
        conf.add_admin("admin@not-forbidden.org")
        conf.start_md(domains)
        conf.add(f"MDCertificateKeyFile {pkey_file}")
        conf.end_md()
        conf.add_vhost(domain)
        conf.install()
        assert env.apache_fail() == 0

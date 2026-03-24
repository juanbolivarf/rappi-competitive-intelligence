/**
 * Universal Android SSL Pinning Bypass
 */

Java.perform(function() {
    console.log("[*] SSL Pinning Bypass loaded");

    // TrustManager bypass
    try {
        var TrustManager = Java.registerClass({
            name: 'com.sensepost.test.TrustManager',
            implements: [Java.use('javax.net.ssl.X509TrustManager')],
            methods: {
                checkClientTrusted: function(chain, authType) {},
                checkServerTrusted: function(chain, authType) {},
                getAcceptedIssuers: function() { return []; }
            }
        });

        var TrustManagers = [TrustManager.$new()];
        var SSLContext = Java.use('javax.net.ssl.SSLContext');
        var SSLContext_init = SSLContext.init.overload(
            '[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom'
        );
        SSLContext_init.implementation = function(keyManager, trustManager, secureRandom) {
            console.log("[*] Bypassing SSLContext.init");
            SSLContext_init.call(this, keyManager, TrustManagers, secureRandom);
        };
        console.log("[+] SSLContext bypass installed");
    } catch(e) {
        console.log("[-] SSLContext bypass failed: " + e);
    }

    // OkHttp3 CertificatePinner bypass
    try {
        var CertificatePinner = Java.use('okhttp3.CertificatePinner');
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, peerCertificates) {
            console.log("[*] OkHttp3 CertificatePinner.check bypassed for: " + hostname);
        };
        console.log("[+] OkHttp3 CertificatePinner bypass installed");
    } catch(e) {
        console.log("[-] OkHttp3 bypass failed: " + e);
    }

    // OkHttp3 newer versions
    try {
        var CertificatePinner2 = Java.use('okhttp3.CertificatePinner');
        CertificatePinner2.check$okhttp.overload('java.lang.String', 'kotlin.jvm.functions.Function0').implementation = function(hostname, func) {
            console.log("[*] OkHttp3 check$okhttp bypassed for: " + hostname);
        };
        console.log("[+] OkHttp3 check$okhttp bypass installed");
    } catch(e) {}

    // TrustManagerImpl bypass
    try {
        var TrustManagerImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TrustManagerImpl.verifyChain.implementation = function(untrustedChain, trustAnchorChain, host, clientAuth, ocspData, tlsSctData) {
            console.log("[*] TrustManagerImpl.verifyChain bypassed for: " + host);
            return untrustedChain;
        };
        console.log("[+] TrustManagerImpl bypass installed");
    } catch(e) {
        console.log("[-] TrustManagerImpl bypass failed: " + e);
    }

    // Network security config bypass
    try {
        var NetworkSecurityConfig = Java.use('android.security.net.config.NetworkSecurityConfig');
        NetworkSecurityConfig.isCleartextTrafficPermitted.overload().implementation = function() {
            console.log("[*] NetworkSecurityConfig.isCleartextTrafficPermitted bypassed");
            return true;
        };
        console.log("[+] NetworkSecurityConfig bypass installed");
    } catch(e) {}

    console.log("[*] SSL Bypass setup complete");
});

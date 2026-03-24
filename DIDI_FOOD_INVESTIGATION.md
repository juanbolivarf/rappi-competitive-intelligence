# DiDi Food Investigation Report

## Summary

DiDi Food presents significant technical challenges for competitive intelligence data collection. Unlike Rappi and Uber Eats, which expose menu and pricing data through server-side rendered (SSR) HTML, DiDi Food implements multiple layers of protection that make automated data extraction extremely difficult.

**Final Status**: DiDi Food scraping is not currently feasible without:
- A rooted Android device, OR
- A jailbroken iOS device, OR
- Manual data collection

For the MVP, we recommend using synthetic data for DiDi Food (available via `--test-data` flag) while collecting real-time data from Rappi and Uber Eats.

---

## Investigation Timeline

### Phase 1: Web-Based Approach

**Attempt**: Access DiDi Food website directly via SSR extraction (same as Rappi/Uber Eats)

**Finding**: DiDi Food website (`https://www.didifood.com/`) has a **login wall** - all menu and pricing data is hidden behind authentication. The website shows:
- Restaurant listings (names and images only)
- No prices
- No delivery fees
- No ETAs
- No menu items

**Blocker**: Authentication required. Cannot extract data from public web pages.

---

### Phase 2: Mobile App API Interception

The mobile app contains all the data we need. The plan was to intercept HTTPS traffic to reverse-engineer the API.

#### 2.1 mitmproxy Setup

**Steps completed**:
1. Installed mitmproxy via pip
2. Started proxy server on `192.168.0.113:8080`
3. Captured HTTP traffic successfully

#### 2.2 iPhone Attempt

**Device**: iPhone (iOS)

**Steps completed**:
1. Configured WiFi proxy to point to mitmproxy
2. Installed mitmproxy CA certificate
3. Opened DiDi Food app

**Result**: Traffic captured showed only encrypted TLS handshakes

**Blocker**: **SSL Certificate Pinning**
iOS apps can verify server certificates match known certificates embedded in the app, blocking proxy interception. Bypassing this requires:
- Jailbroken device with SSL Kill Switch 2
- Frida with SSL bypass scripts (requires jailbreak)

---

### Phase 3: Android Phone (Non-Rooted)

**Device**: Redmi Note 12C (Android, not rooted)

#### 3.1 Frida Server Approach

**Frida** is a dynamic instrumentation toolkit that can hook into running apps and bypass SSL pinning.

**Steps completed**:
1. Enabled USB debugging on phone
2. Connected via ADB (Android Debug Bridge)
3. Downloaded Frida server (ARM64 version)
4. Attempted to push Frida server to device

**Result**: `su: inaccessible or not found`

**Blocker**: **Root access required**
Frida server requires root (superuser) access to hook into app processes. Consumer Android phones are not rooted by default.

#### 3.2 HTTP Toolkit Approach

HTTP Toolkit is a user-friendly alternative that claims to work on some non-rooted devices.

**Steps completed**:
1. Downloaded and installed HTTP Toolkit
2. Connected to Android device via ADB
3. Configured proxy settings

**Result**: Logs showed `Root not available, skipping cert injection`

**Blocker**: **Root access required**
HTTP Toolkit's ADB interception also requires root to inject certificates into the system certificate store.

---

### Phase 4: Android Emulator (Rooted)

Android emulators with Google APIs (not Play Store) images can run as root.

#### 4.1 Emulator Setup

**Steps completed**:
1. Downloaded Android SDK command-line tools
2. Downloaded OpenJDK 21
3. Installed:
   - `emulator` package
   - `platform-tools` (ADB)
   - `system-images;android-30;google_apis;x86_64`
4. Created AVD (Android Virtual Device) named `didi_test2`
5. Started emulator with `-writable-system` flag
6. Confirmed root access via `adb root`

#### 4.2 DiDi Food Installation

**Steps completed**:
1. Extracted DiDi Food APK from user's physical phone:
   - Base APK: `base.apk` (132MB)
   - Split APKs for architecture and DPI
2. Installed APK on emulator: `adb install didi_food.apk`
3. Installation successful

#### 4.3 Frida Server Setup

**Steps completed**:
1. Downloaded Frida server for x86_64 architecture
2. Pushed to emulator: `/data/local/tmp/frida-server`
3. Made executable: `chmod +x`
4. Created SSL bypass script (`ssl_bypass.js`) with:
   - TrustManager bypass
   - OkHttp3 CertificatePinner bypass
   - TrustManagerImpl bypass
   - NetworkSecurityConfig bypass

#### 4.4 Network Connectivity Issue

**Problem**: DiDi Food app would not launch properly

**Diagnosis**:
- `ping 8.8.8.8` returned 100% packet loss
- Internal gateway (10.0.2.2) was reachable
- DNS server (10.0.2.3) was reachable
- Missing default route in routing table
- Added route: `ip route add default via 10.0.2.2 dev eth0`

**Blocker**: **Emulator network configuration**
Even after adding the default route, external internet connectivity failed. This appears to be a Windows firewall or NAT issue with the Android emulator's network stack.

**Additional attempts**:
- Restarted emulator with `-dns-server 8.8.8.8,8.8.4.4`
- Verified iptables rules (all ACCEPT policies)
- Checked airplane mode (disabled)

The emulator could reach its local gateway but could not reach the internet.

---

## Technical Blockers Summary

| Approach | Blocker | Possible Solution |
|----------|---------|-------------------|
| Web SSR | Login wall | N/A - data not exposed |
| iPhone proxy | SSL pinning | Jailbreak + SSL Kill Switch |
| Android proxy | SSL pinning | Root + Frida |
| HTTP Toolkit | Root required | Root the device |
| Android emulator | Network connectivity | Debug Windows firewall/NAT |

---

## Files Created During Investigation

| File | Purpose |
|------|---------|
| `ssl_bypass.js` | Frida script for SSL pinning bypass |
| `didi_capture.flow` | mitmproxy capture file (21MB) |
| `didi_emulator_capture.flow` | Emulator capture attempt |

---

## Recommended Next Steps

### Option A: Continue with DiDi Food (High Effort)

1. **Fix emulator networking**
   - Debug Windows Firewall rules
   - Try Linux or macOS host (better emulator support)
   - Try Genymotion emulator (commercial, better networking)

2. **Alternative: Cloud Android device**
   - Services like AWS Device Farm or Firebase Test Lab
   - Pre-rooted Android images available

3. **Alternative: Root physical device**
   - Older Android phones are easier to root
   - Risk: may brick device, voids warranty

### Option B: Use Synthetic Data (Recommended for MVP)

The synthetic data generator (`synthetic_data.py`) creates realistic DiDi Food pricing based on observed market patterns:

- **Price multiplier**: 0.93x (7% cheaper than baseline - aggressive pricing strategy)
- **Delivery fees**: Highest peripheral premium (+$18 MXN in low-income zones)
- **Service fee**: 8% (lowest among platforms)
- **Promo probability**: 45% (most aggressive promotions)
- **Coverage**: 82% availability rate (lowest coverage)

Usage:
```bash
python main.py --test-data
```

This generates data for all 3 platforms with realistic competitive dynamics.

### Option C: Manual Data Collection

For accurate DiDi Food data:
1. Open DiDi Food app on phone
2. Search for target restaurants
3. Record prices, fees, and ETAs manually
4. Import into the system via CSV

---

## Conclusion

DiDi Food's aggressive security measures (SSL pinning, login walls) are designed to protect their pricing data from competitive intelligence gathering. While technically possible to bypass with rooted devices, the effort required exceeds the MVP scope.

The synthetic data approach provides realistic market dynamics for analysis and visualization purposes, while real-time scraping focuses on the accessible platforms (Rappi and Uber Eats).

---

## References

- [Frida Documentation](https://frida.re/docs/)
- [SSL Pinning Bypass Techniques](https://blog.netspi.com/four-ways-to-bypass-android-ssl-verification-and-certificate-pinning/)
- [Android Emulator Networking](https://developer.android.com/studio/run/emulator-networking)
- [mitmproxy Documentation](https://docs.mitmproxy.org/)

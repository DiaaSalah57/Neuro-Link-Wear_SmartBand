// =====================================================
//          WiFi Provisioning (Captive Portal)
// =====================================================
// Saves SSID + password to ESP32 NVS (non-volatile storage)
// so you never have to re-flash the firmware to change
// the network. If no credentials are saved, or the saved
// ones fail, the ESP32 starts an AP + Captive Portal
// where you can pick a network and enter the password
// from your phone.
// =====================================================
#ifndef WIFI_PROVISIONING_H
#define WIFI_PROVISIONING_H

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>

// NVS namespace + keys
#define NVS_NAMESPACE   "wifi"
#define NVS_KEY_SSID    "ssid"
#define NVS_KEY_PASS    "pass"

// AP (setup) network name — change if you want
const char* AP_NAME = "NeuroLink-Setup";
const char* AP_PASS = "";   // open AP (no password) for easier phone pairing

// How long to wait for STA connection before falling back to AP
const uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000;

// Hold the BOOT (GPIO0) button for this long during boot to
// skip stored credentials and enter the setup portal.
const uint32_t FACTORY_RESET_HOLD_MS = 4000;

// DNS server for captive portal (forces redirect to setup page)
const byte DNS_PORT = 53;

// Captive portal HTML — embedded so no filesystem is required.
// Includes a simple network scanner + manual entry form.
static const char PORTAL_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NeuroLink Setup</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:16px}
 h1{color:#38bdf8;font-size:20px;margin:0 0 4px}
 p.sub{color:#94a3b8;font-size:13px;margin:0 0 16px}
 .card{background:#1e293b;border-radius:12px;padding:16px;margin-bottom:14px}
 label{display:block;font-size:12px;color:#94a3b8;margin:10px 0 4px}
 input,select{width:100%;padding:10px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:15px;box-sizing:border-box}
 button{width:100%;padding:12px;border:0;border-radius:10px;background:#38bdf8;color:#0f172a;font-weight:700;font-size:15px;margin-top:14px;cursor:pointer}
 button.secondary{background:#334155;color:#e2e8f0}
 .net{display:flex;justify-content:space-between;align-items:center;padding:8px;border-radius:6px}
 .net:hover{background:#334155;cursor:pointer}
 .rssi{color:#94a3b8;font-size:12px}
 .saved{color:#4ade80;font-size:12px;margin-top:8px}
</style></head><body>
<h1>NeuroLink Wear &mdash; WiFi Setup</h1>
<p class="sub">Pick a scanned network or enter one manually.</p>
<form method="POST" action="/save">
 <div class="card">
  <label>Saved network</label>
  <div id="saved" class="sub">checking...</div>
  <label>Scanned networks (tap to fill)</label>
  <div id="list">scanning...</div>
 </div>
 <div class="card">
  <label>SSID</label>
  <input id="ssid" name="ssid" required>
  <label>Password</label>
  <input id="pass" name="pass" type="password">
  <button type="submit">Save &amp; Connect</button>
  <button class="secondary" type="button" onclick="document.getElementById('pass').value='';document.getElementById('ssid').value=''">Clear saved network</button>
 </div>
</form>
<script>
fetch('/api/status').then(r=>r.json()).then(s=>{
 document.getElementById('saved').innerText =
   (s.saved_ssid && s.saved_ssid.length) ? ('Current: ' + s.saved_ssid) : 'Nothing saved yet.';
});
fetch('/api/scan').then(r=>r.json()).then(list=>{
 const c=document.getElementById('list'); c.innerHTML='';
 if(!list.length){ c.innerText='No networks found.'; return; }
 list.forEach(n=>{
   const d=document.createElement('div'); d.className='net';
   d.innerHTML='<span>'+n.ssid+'</span><span class="rssi">'+n.rssi+' dBm</span>';
   d.onclick=()=>{ document.getElementById('ssid').value=n.ssid; document.getElementById('pass').focus(); };
   c.appendChild(d);
 });
});
// Common mobile-portal probes -> make captive portal pop up
window.addEventListener('load',()=>{ /* nothing extra needed */ });
</script>
</body></html>
)HTML";

Preferences prefs;
WebServer   portalServer(80);
DNSServer   portalDns;
bool        provisioningActive = false;

// ---------------------------------------------------------
// Save / load / clear credentials in NVS
// ---------------------------------------------------------
void saveWifiCredentials(const String& ssid, const String& pass) {
  prefs.begin(NVS_NAMESPACE, false);
  prefs.putString(NVS_KEY_SSID, ssid);
  prefs.putString(NVS_KEY_PASS, pass);
  prefs.end();
}

bool loadWifiCredentials(String& ssid, String& pass) {
  prefs.begin(NVS_NAMESPACE, true); // read-only
  ssid = prefs.getString(NVS_KEY_SSID, "");
  pass = prefs.getString(NVS_KEY_PASS, "");
  prefs.end();
  return ssid.length() > 0;
}

void clearWifiCredentials() {
  prefs.begin(NVS_NAMESPACE, false);
  prefs.remove(NVS_KEY_SSID);
  prefs.remove(NVS_KEY_PASS);
  prefs.end();
}

// ---------------------------------------------------------
// Portal handlers
// ---------------------------------------------------------
void handleRoot() {
  portalServer.send(200, "text/html", PORTAL_HTML);
}

void handleSave() {
  String ssid = portalServer.arg("ssid");
  String pass = portalServer.arg("pass");
  if (ssid.length() == 0) {
    portalServer.send(400, "text/html",
      "<meta http-equiv='refresh' content='2;url=/'><body style='font-family:sans-serif;background:#0f172a;color:#e2e8f0'>"
      "<p>SSID is required. Going back...</p></body>");
    return;
  }
  saveWifiCredentials(ssid, pass);
  portalServer.send(200, "text/html",
    "<meta http-equiv='refresh' content='5;url=/'>"
    "<body style='font-family:sans-serif;background:#0f172a;color:#e2e8f0;text-align:center;padding:40px'>"
    "<h1 style='color:#38bdf8'>Saved!</h1>"
    "<p>Connecting to <b>" + ssid + "</b>... the device will reboot.</p></body>");

  // Schedule a reboot so the normal STA path takes over cleanly.
  delay(800);
  ESP.restart();
}

void handleClear() {
  clearWifiCredentials();
  portalServer.send(200, "text/html",
    "<meta http-equiv='refresh' content='3;url=/'>"
    "<body style='font-family:sans-serif;background:#0f172a;color:#e2e8f0;text-align:center;padding:40px'>"
    "<h1 style='color:#38bdf8'>Cleared</h1><p>Rebooting...</p></body>");
  delay(600);
  ESP.restart();
}

void handleApiStatus() {
  String ssid, pass;
  loadWifiCredentials(ssid, pass);
  String json = "{\"saved_ssid\":\"" + ssid + "\",";
  json += "\"ap_ip\":\"" + WiFi.softAPIP().toString() + "\"}";
  portalServer.send(200, "application/json", json);
}

void handleApiScan() {
  // Scan must be done in STA mode, but the chip is currently in APSTA.
  int n = WiFi.scanNetworks(false, true); // async=false, show_hidden=true
  String json = "[";
  for (int i = 0; i < n; i++) {
    if (i) json += ",";
    json += "{\"ssid\":\"" + WiFi.SSID(i) + "\",\"rssi\":" + WiFi.RSSI(i) + "}";
  }
  json += "]";
  portalServer.send(200, "application/json", json);
  WiFi.scanDelete();
}

// Captive-portal probe handler: any unknown host -> root page.
// This is what makes Android/iOS pop up the "Sign in" dialog automatically.
void handleCaptive() {
  portalServer.sendHeader("Location", "http://192.168.4.1/", true);
  portalServer.send(302, "text/plain", "");
}

// ---------------------------------------------------------
// Start the setup AP + portal
// ---------------------------------------------------------
void startProvisioningPortal() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_NAME, AP_PASS, 1, 0, 4); // channel 1, open, 4 max clients

  portalDns.start(DNS_PORT, "*", WiFi.softAPIP());

  portalServer.on("/",             handleRoot);
  portalServer.on("/save",        HTTP_POST, handleSave);
  portalServer.on("/clear",       HTTP_POST, handleClear);
  portalServer.on("/api/status",  handleApiStatus);
  portalServer.on("/api/scan",    handleApiScan);
  // Common captive-portal detection URLs from phones
  portalServer.on("/generate_204", handleCaptive);  // Android
  portalServer.on("/hotspot-detect.html", handleCaptive); // Apple
  portalServer.on("/connecttest.txt", handleCaptive); // Windows
  portalServer.onNotFound(handleCaptive);

  portalServer.begin();
  provisioningActive = true;
}

void stopProvisioningPortal() {
  if (provisioningActive) {
    portalServer.stop();
    portalDns.stop();
    WiFi.softAPdisconnect(true);
    provisioningActive = false;
  }
}

// ---------------------------------------------------------
// Public: call from setup() BEFORE sensor init if you like
// Returns true if connected, false if portal is running.
// ---------------------------------------------------------
bool wifiProvisionConnect() {
  String ssid, pass;

  // ---- Factory-reset check: hold BOOT (GPIO0) at boot ----
  pinMode(0, INPUT_PULLUP);
  if (digitalRead(0) == LOW) {
    Serial.println("[WiFi] BOOT held at startup. Hold for 4s to forget network...");
    uint32_t t0 = millis();
    bool wasHeld = true;
    while (digitalRead(0) == LOW && millis() - t0 < FACTORY_RESET_HOLD_MS) {
      delay(50);
    }
    if (millis() - t0 >= FACTORY_RESET_HOLD_MS) {
      Serial.println("[WiFi] BOOT held long enough -> clearing saved credentials.");
      clearWifiCredentials();
      // fall through into the portal below
    } else {
      Serial.println("[WiFi] BOOT released early -> keeping saved credentials.");
    }
  }

  if (!loadWifiCredentials(ssid, pass)) {
    Serial.println("[WiFi] No saved credentials -> starting setup portal.");
    startProvisioningPortal();
    return false;
  }

  Serial.printf("[WiFi] Connecting to saved network '%s'...\n", ssid.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(), pass.c_str());

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    return true;
  }

  Serial.println("[WiFi] Saved credentials failed -> starting setup portal.");
  // Don't auto-clear the saved creds; user may want to fix and retry.
  startProvisioningPortal();
  return false;
}

void wifiProvisionLoop() {
  if (provisioningActive) {
    portalDns.processNextRequest();
    portalServer.handleClient();
  }
}

#endif // WIFI_PROVISIONING_H
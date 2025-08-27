#include "WiFi.h"
#include "esp_camera.h"
#include "esp_http_client.h"
#include "Arduino.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <ArduinoJson.h>
#include <WebSocketsClient.h>

// OLED Configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define OLED_SDA      15
#define OLED_SCL      14

String displayMessages[5];

// Touch Sensor Pin
#define TOUCH_PIN     4  // Touch sensor SIG on IO4 (GPIO 4)
#define FLASH_GPIO_NUM  2 

// WiFi credentials
const char* ssid = "esp"; 
const char* password = "12345679";

// FastAPI server details
char* serverUrl = "http://192.168.6.219:8000/upload";

// WebSocket Configuration
const char* websocket_server = "192.168.6.219";
const uint16_t websocket_port = 8000;
const char* websocket_path = "/audio-stream";

// Camera pins for ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

Adafruit_SH1106G display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
WebSocketsClient webSocket;

// Touch detection variables

int modeCounter = 0;
unsigned long lastImageSentTime = 0;
bool lastTouchState = false;

void setup() {
  Serial.begin(115200);
  Serial.println("started");

  
  displayMessages[0] = "Idle Mode";
  displayMessages[1] = "Translation Started";
  displayMessages[2] = "Image Translation Started";
  displayMessages[3] = "Sign Language Translation Started";
  displayMessages[4] = "Alert Mode";

  // Initialize touch sensor pin with internal pull-up
  pinMode(TOUCH_PIN, INPUT_PULLUP);

  // Initialize flash pin
  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW); // Ensure flash is off initially

  // Initialize OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(0x3C, true)) {
    Serial.println("SH1106 allocation failed");
    while (true);
  }
  
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(0, 10);
  display.println("Connecting...");
  display.display();

  // Configure the camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_RGB565;
  
  if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA; // 800x600
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera initialization failed with error 0x%x", err);
    display.clearDisplay();
    display.setCursor(0, 10);
    display.println("Camera Init Failed");
    display.display();
    while (true);
  }
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected to WiFi, IP address: ");
  Serial.println(WiFi.localIP());

  // Update OLED with connection status
  display.clearDisplay();
  display.setCursor(0, 10);
  display.println("WiFi Connected");
  display.setCursor(0, 30);
  display.println(WiFi.localIP().toString());
  display.display();

  // Initialize WebSocket
  webSocket.begin(websocket_server, websocket_port, websocket_path);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
}

// WebSocket event handler
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("WebSocket Disconnected");
      break;
    case WStype_CONNECTED:
      Serial.println("WebSocket Connected");
      webSocket.sendTXT("Hello from ESP32");
      break;
    case WStype_TEXT: {
      if(modeCounter == 1){
          // Create a new scope for WStype_TEXT
      String receivedText = String((char*)payload);
      
      // Clear display
      display.clearDisplay();
      display.setTextSize(0.5);
      display.setTextColor(SH110X_WHITE);
      display.setCursor(0, 10);
      
      // Truncate if too long
      if (receivedText.length() > 40) {
        receivedText = receivedText.substring(0, 20);
      }
      
      // Split text into two lines if needed
      if (receivedText.length() > 20) {
        display.println(receivedText.substring(0, 20));
        display.setCursor(0, 30);
        display.println(receivedText.substring(20));
      } else {
        display.println(receivedText);
      }
      
      display.display();
      Serial.printf("Received: %s\n", payload);
      break;
      }
    }
    case WStype_PING:
      Serial.println("Ping received");
      break;
    case WStype_PONG:
      Serial.println("Pong received");
      break;
  }
}

// HTTP event handler
esp_err_t http_event_handler(esp_http_client_event_t *evt) {
  switch (evt->event_id) {
    case HTTP_EVENT_ON_DATA: {
      Serial.printf("HTTP_EVENT_ON_DATA, len=%d\n", evt->data_len);
      if (evt->data_len) {
        String response = String((char*)evt->data);
        Serial.println(response);
        StaticJsonDocument<512> doc;
        DeserializationError error = deserializeJson(doc, response);
        if (error) {
          Serial.printf("JSON parse failed: %s\n", error.c_str());
          break;
        }

        const char* message = doc["message"];
        String displayText = message ? String(message) : "No message";

        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SH110X_WHITE);
        display.setCursor(0, 10);
        if (displayText.length() > 40) {
          displayText = displayText.substring(0, 40);
        }
        if (displayText.length() > 20) {
          display.println(displayText.substring(0, 20));
          display.setCursor(0, 30);
          display.println(displayText.substring(20));
        } else {
          display.println(displayText);
        }
        display.display();
      }
      break;
    }
    case HTTP_EVENT_ERROR:
      Serial.println("HTTP_EVENT_ERROR");
      break;
    case HTTP_EVENT_DISCONNECTED:
      Serial.println("HTTP_EVENT_DISCONNECTED");
      break;
    default:
      break;
  }
  return ESP_OK;
}

void captureAndSendImage() {
  digitalWrite(FLASH_GPIO_NUM, HIGH);
  delay(100);
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    display.clearDisplay();
    display.setCursor(0, 10);
    display.println("Capture Failed");
    display.display();
    return;
  }
  
  digitalWrite(FLASH_GPIO_NUM, LOW);
  
  Serial.println("Image captured");
  Serial.printf("Image size: %d bytes\n", fb->len);
  Serial.printf("Image format: %d (RGB565=%d)\n", fb->format, PIXFORMAT_RGB565);
  Serial.printf("Image width: %d, height: %d\n", fb->width, fb->height);
  esp_http_client_config_t config = {0};
  config.url = serverUrl;
  config.event_handler = http_event_handler;
  config.timeout_ms = 10000;
  
  esp_http_client_handle_t client = esp_http_client_init(&config);
  
  esp_http_client_set_header(client, "Content-Type", "application/octet-stream");
  esp_http_client_set_header(client, "X-Image-Width", String(fb->width).c_str());
  esp_http_client_set_header(client, "X-Image-Height", String(fb->height).c_str());
  esp_http_client_set_header(client, "X-Image-Format", "rgb565");
  
  esp_http_client_set_method(client, HTTP_METHOD_POST);
  esp_http_client_set_post_field(client, (const char *)fb->buf, fb->len);
  
  esp_err_t err = esp_http_client_perform(client);
  
  if (err == ESP_OK) {
    int status_code = esp_http_client_get_status_code(client);
    Serial.printf("HTTP POST status = %d\n", status_code);
  } else {
    Serial.printf("HTTP POST request failed: %s\n", esp_err_to_name(err));
    display.clearDisplay();
    display.setCursor(0, 10);
    display.println("POST Failed");
    display.display();
  }
  
  esp_http_client_cleanup(client);
  esp_camera_fb_return(fb);
}


void loop() {

  webSocket.loop();  // Always keep this running!
  bool currentTouchState = digitalRead(TOUCH_PIN) == HIGH;
  
  if (currentTouchState && !lastTouchState) {
    modeCounter = (modeCounter + 1) % 4;
    Serial.printf("Mode changed to: %d\n", modeCounter);
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SH110X_WHITE);
    display.setCursor(0, 10);
    display.printf(displayMessages[modeCounter].c_str());
    display.display();
  }

  lastTouchState = currentTouchState;

  // Handle different modes
  switch (modeCounter) {
    case 0:
      // Idle, do nothing
      break;

    case 1:
      break;
      
    case 2:
      // Send image every 1 second to /upload
      if (millis() - lastImageSentTime >= 1000) {
        serverUrl = "http://192.168.6.219:8000/upload";
        captureAndSendImage();
        lastImageSentTime = millis();
      }
      break;
    case 3:
      // Send image every 1 second to /signlanguage
      if (millis() - lastImageSentTime >= 1000) {
        serverUrl = "http://192.168.6.219:8000/sign_language";
        captureAndSendImage();
        lastImageSentTime = millis();
      }
      break;
  }
}
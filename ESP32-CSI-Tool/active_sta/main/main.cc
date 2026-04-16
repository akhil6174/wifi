#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_log.h"
#include "driver/uart.h"    
#include "esp_timer.h"     

#define SSID "CSI_AP"
#define PASS "12345678"
#define CHANNEL 6

static const char *TAG = "CSI_STA";

uint8_t ap_mac[6] = {0xA4,0xF0,0x0F,0x5B,0x78,0x25};

wifi_csi_config_t csi_config = {
    .lltf_en = true,
    .htltf_en = true,
    .stbc_htltf2_en = true,
    .ltf_merge_en = true,
    .channel_filter_en = true,
    .manu_scale = false,
    .shift = 0,
    .dump_ack_en = false
};

// --- 1. CSI CALLBACK ---
static void csi_rx_cb(void *ctx, wifi_csi_info_t *info)
{
    if (!info) return;
    if (memcmp(info->mac, ap_mac, 6) != 0) return;

    int64_t timestamp = esp_timer_get_time();

    // Format: CSI, Timestamp, MAC, RSSI, LEN, Data...
    printf("CSI,%lld,%02X:%02X:%02X:%02X:%02X:%02X,%d,%d,", 
           timestamp,
           info->mac[0], info->mac[1], info->mac[2], 
           info->mac[3], info->mac[4], info->mac[5],
           info->rx_ctrl.rssi, 
           info->len);

    for (int i = 0; i < info->len; i++) {
        printf("%d%c", info->buf[i], (i == info->len - 1) ? '\n' : ',');
    }
}

// --- 2. START CSI ---
void start_csi()
{
    esp_wifi_set_promiscuous(true);
    wifi_promiscuous_filter_t filt = { .filter_mask = WIFI_PROMIS_FILTER_MASK_DATA };
    esp_wifi_set_promiscuous_filter(&filt);
    esp_wifi_set_csi_config(&csi_config);
    esp_wifi_set_csi_rx_cb(&csi_rx_cb, NULL);
    esp_wifi_set_csi(true);
    ESP_LOGI(TAG, "CSI Started");
}

// --- 3. EVENT HANDLER ---
static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11N);
        esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BW_HT20);
        start_csi();
    }
}

// --- 4. WIFI INIT ---
void wifi_init_sta()
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    cfg.static_rx_buf_num = 20;
    cfg.dynamic_rx_buf_num = 64;
    esp_wifi_init(&cfg);

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL);
    
    wifi_config_t sta_config = {};
    strcpy((char*)sta_config.sta.ssid, SSID);
    strcpy((char*)sta_config.sta.password, PASS);
    sta_config.sta.channel = CHANNEL;
    sta_config.sta.scan_method = WIFI_FAST_SCAN;

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &sta_config);
    esp_wifi_start();
    esp_wifi_set_ps(WIFI_PS_NONE);
}

// --- 5. MAIN ---
extern "C" void app_main()
{
    ESP_ERROR_CHECK(nvs_flash_init());

    // Updated UART Config to remove warnings
    uart_config_t uart_config = {
        .baud_rate = 921600,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT, // Explicitly set clock to avoid anonymous member warning
    };
    
    ESP_ERROR_CHECK(uart_param_config(UART_NUM_0, &uart_config));

    wifi_init_sta();
}
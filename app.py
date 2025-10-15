﻿import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- Sayfa Ayarları ve Başlık ---
st.set_page_config(
    page_title="Kripto Veri Paneli",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Kripto Finansal Paneli")

# --- API Anahtarı ---
# Kendi API anahtarını buraya yapıştırmayı unutma!
API_KEY = st.secrets["api_key"]

# --- Coin Listesi ---
COIN_LISTESI = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Toncoin": "the-open-network",
    "Aave": "aave",
    "PancakeSwap (Cake)": "pancakeswap-token",
    "Uniswap": "uniswap"
}

# --- YARDIMCI FONKSİYON: BÜYÜK SAYILARI FORMATLAMA ---
def format_large_number(num):
    """Büyük sayıları Mln, Mlr, T olarak formatlar."""
    if num is None: return "$0"
    if num > 1_000_000_000_000: return f"${num / 1_000_000_000_000:.2f} T"
    if num > 1_000_000_000: return f"${num / 1_000_000_000:.2f} Mlr"
    if num > 1_000_000: return f"${num / 1_000_000:.2f} Mln"
    return f"${num:,.2f}"

# --- API FONKSİYONLARI ---
def get_coin_market_data(coin_id):
    """Seçilen coinin anlık piyasa verilerini çeker."""
    URL = 'https://api.coingecko.com/api/v3/coins/markets'
    PARAMETRELER = {'vs_currency': 'usd', 'ids': coin_id, 'x_cg_demo_api_key': API_KEY}
    try:
        response = requests.get(url=URL, params=PARAMETRELER)
        response.raise_for_status()
        return response.json()[0]
    except Exception: return None

def get_ohlc_data_for_period(coin_id, days):
    """Belirtilen PERİYOT için doğrudan API'dan günlük OHLC verisi çeker (Mum Grafiği için)."""
    URL = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    PARAMETRELER = {'vs_currency': 'usd', 'days': days, 'x_cg_demo_api_key': API_KEY}
    try:
        response = requests.get(url=URL, params=PARAMETRELER)
        response.raise_for_status()
        veri = response.json()
        df = pd.DataFrame(veri, columns=['timestamp', 'Open', 'High', 'Low', 'Close'])
        df['Tarih'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Tarih', inplace=True)
        return df
    except Exception: return None

def get_price_data_for_range(coin_id, start_datetime, end_datetime):
    """Belirtilen TARİH ARALIĞI için fiyat verisi çeker (Çizgi Grafiği için)."""
    start_timestamp = int(start_datetime.timestamp())
    end_timestamp = int(end_datetime.timestamp())
    URL = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    PARAMETRELER = {'vs_currency': 'usd', 'from': start_timestamp, 'to': end_timestamp, 'x_cg_demo_api_key': API_KEY}
    try:
        response = requests.get(url=URL, params=PARAMETRELER)
        response.raise_for_status()
        veri = response.json()['prices']
        df = pd.DataFrame(veri, columns=['timestamp', 'Fiyat (USD)'])
        df['Tarih'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['Tarih', 'Fiyat (USD)']].set_index('Tarih')
        return df
    except Exception: return None

# --- ARAYÜZ (SIDEBAR) ---
st.sidebar.title("Ayarlar")
secilen_coin_adi = st.sidebar.selectbox('Coin Seçin:', list(COIN_LISTESI.keys()))

analiz_turu = st.sidebar.radio("Analiz Türü Seçin:", ["Periyot", "Özel Tarih Aralığı"])

if analiz_turu == "Periyot":
    zaman_araliklari = {"Son 7 Gün": 7, "Son 30 Gün": 30, "Son 90 Gün": 90, "Son 1 Yıl": 365}
    secilen_aralik_adi = st.sidebar.selectbox("Periyot Seçin:", zaman_araliklari.keys())
    secilen_gun_sayisi = zaman_araliklari[secilen_aralik_adi]
else:
    bugun = datetime.now().date()
    baslangic_tarihi = st.sidebar.date_input("Başlangıç Tarihi", bugun - pd.Timedelta(days=30))
    bitis_tarihi = st.sidebar.date_input("Bitiş Tarihi", bugun)

# --- ANA EKRAN ---
secilen_coin_id = COIN_LISTESI[secilen_coin_adi]
main_col, details_col = st.columns([2.5, 1])

with main_col:
    st.header(f"{secilen_coin_adi} Fiyat Analizi")
    market_data = get_coin_market_data(secilen_coin_id)
    if market_data:
        st.metric(label="Anlık Fiyat (USD)", value=f"${market_data.get('current_price', 0):,.2f}", delta=f"{market_data.get('price_change_percentage_24h', 0):.2f}%")
    else: st.warning("Anlık piyasa verileri alınamadı.")

    # Seçilen analiz türüne göre doğru grafiği çizdir
    if analiz_turu == "Periyot":
        st.subheader(f"Tarihsel Fiyat Grafiği ({secilen_aralik_adi}) - Mum Grafiği")
        with st.spinner('Mum grafiği için veriler yükleniyor...'):
            ohlc_df = get_ohlc_data_for_period(secilen_coin_id, secilen_gun_sayisi)
            if ohlc_df is not None and not ohlc_df.empty:
                fig = go.Figure(data=[go.Candlestick(x=ohlc_df.index, open=ohlc_df['Open'], high=ohlc_df['High'], low=ohlc_df['Low'], close=ohlc_df['Close'], increasing_line_color='lime', decreasing_line_color='red')])
                fig.update_layout(xaxis_rangeslider_visible=False, yaxis_title="Fiyat (USD)", xaxis_title="Tarih", template="plotly_dark", height=500, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Seçilen periyot için grafik verisi bulunamadı.")
    else: # Analiz Türü "Özel Tarih Aralığı" ise
        st.subheader(f"{baslangic_tarihi} - {bitis_tarihi} Arası - Çizgi Grafiği")
        if baslangic_tarihi >= bitis_tarihi:
            st.error("Hata: Başlangıç tarihi, bitiş tarihinden sonra veya aynı olamaz.")
        else:
            # 'date' objesini 'datetime' objesine çeviriyoruz
            start_datetime = datetime.combine(baslangic_tarihi, datetime.min.time())
            end_datetime = datetime.combine(bitis_tarihi, datetime.max.time())
            
            with st.spinner('Çizgi grafiği için veriler yükleniyor...'):
                price_df = get_price_data_for_range(secilen_coin_id, start_datetime, end_datetime)
                if price_df is not None and not price_df.empty:
                    st.line_chart(price_df)
                else: st.warning("Seçilen tarih aralığı için veri bulunamadı.")

with details_col:
    st.header("Piyasa Detayları")
    # market_data'yı burada tekrar çekmeye gerek yok, yukarıda zaten çekilmişti.
    if market_data:
        detay_verileri = {
            "Metrik": ["Piyasa Değeri", "24s Hacim", "24s En Yüksek", "24s En Düşük", "Dolaşımdaki Arz", "Toplam Arz"],
            "Değer": [
                format_large_number(market_data.get('market_cap', 0)),
                format_large_number(market_data.get('total_volume', 0)),
                f"${market_data.get('high_24h', 0):,.2f}",
                f"${market_data.get('low_24h', 0):,.2f}",
                f"{market_data.get('circulating_supply', 0):,} {market_data.get('symbol', '').upper()}",
                f"{market_data.get('total_supply', 0):,}" if market_data.get('total_supply') else "N/A"
            ]
        }
        df_detaylar = pd.DataFrame(detay_verileri).set_index("Metrik")
        st.table(df_detaylar)
    else: st.warning("Detay verileri alınamadı.")

st.sidebar.info("Bu panel, CoinGecko API'si kullanılarak anlık ve tarihsel veri çekmektedir.")
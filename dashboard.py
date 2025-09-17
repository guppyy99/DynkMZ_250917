import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, date, timedelta
import os
import requests
import json
import time

# .env 파일 로드 (선택사항)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv가 설치되지 않은 경우 무시

# 페이지 설정
st.set_page_config(
    page_title="골프 날씨 트렌드 대시보드",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2E8B57;
        margin: 0.5rem 0;
    }
    .weather-card {
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
    .rain-card { background-color: #e3f2fd; }
    .snow-card { background-color: #f3e5f5; }
    .dry-card { background-color: #fff3e0; }
    .mixed-card { background-color: #f1f8e9; }
</style>
""", unsafe_allow_html=True)

def fetch_naver_datalab_daily(keyword_groups, start_date, end_date):
    """네이버 데이터랩에서 검색 트렌드 데이터 가져오기"""
    url = "https://openapi.naver.com/v1/datalab/search"
    
    # API 키 가져오기 (환경변수 -> Streamlit secrets 순서)
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    
    # Streamlit secrets에서 시도
    if not client_id or not client_secret:
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'NAVER_CLIENT_ID' in st.secrets:
                client_id = st.secrets['NAVER_CLIENT_ID']
                client_secret = st.secrets['NAVER_CLIENT_SECRET']
        except:
            pass
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }
    
    if not client_id or not client_secret:
        st.error("⚠️ 네이버 API 자격증명이 설정되지 않았습니다.")
        st.info("""
        **API 키 설정 방법:**
        1. **로컬 실행**: 환경변수 설정
           ```bash
           export NAVER_CLIENT_ID="your_client_id"
           export NAVER_CLIENT_SECRET="your_client_secret"
           ```
        2. **Streamlit Cloud**: Secrets에서 설정
           - Settings → Secrets → 다음 내용 추가:
           ```
           NAVER_CLIENT_ID = "your_client_id"
           NAVER_CLIENT_SECRET = "your_client_secret"
           ```
        """)
        return None
    
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "date",
        "keywordGroups": keyword_groups,
    }
    
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        rows = []
        for group in data.get("results", []):
            gname = group["title"]
            for item in group["data"]:
                rows.append({
                    "date": item["period"],
                    "group": gname,
                    "ratio": item["ratio"]
                })
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        return df
        
    except requests.exceptions.RequestException as e:
        st.error(f"네이버 API 호출 중 오류가 발생했습니다: {e}")
        return None
    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
        return None

def fetch_open_meteo_daily(lat, lon, start_date, end_date, tz):
    """Open-Meteo에서 날씨 데이터 가져오기"""
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum,snowfall_sum",
        "timezone": tz,
    }
    
    try:
        r = requests.get(base_url, params=params, timeout=60)
        r.raise_for_status()
        js = r.json()
        daily = js.get("daily", {})
        
        df = pd.DataFrame({
            "date": pd.to_datetime(daily.get("time", [])).date,
            "precipitation_sum": daily.get("precipitation_sum", []),
            "rain_sum": daily.get("rain_sum", []),
            "snowfall_sum": daily.get("snowfall_sum", []),
        })
        return df
        
    except requests.exceptions.RequestException as e:
        st.error(f"날씨 API 호출 중 오류가 발생했습니다: {e}")
        return None
    except Exception as e:
        st.error(f"날씨 데이터 처리 중 오류가 발생했습니다: {e}")
        return None

def classify_weather(row, rain_threshold=1.0, snow_threshold=1.0):
    """날씨 분류"""
    rain = row.get("rain_sum", 0.0) or 0.0
    snow = row.get("snowfall_sum", 0.0) or 0.0
    
    if rain >= rain_threshold and snow >= snow_threshold:
        return "mixed"
    if snow >= snow_threshold:
        return "snow"
    if rain >= rain_threshold:
        return "rain"
    return "dry"

@st.cache_data(ttl=300)  # 5분 캐시
def load_data_with_keywords(keyword_groups, start_date, end_date, lat=37.5665, lon=126.9780, tz="Asia/Seoul"):
    """키워드와 날짜를 받아서 데이터 로딩 및 전처리"""
    # 네이버 데이터 가져오기
    df_trend = fetch_naver_datalab_daily(keyword_groups, start_date, end_date)
    if df_trend is None or df_trend.empty:
        return None, None
    
    # 날씨 데이터 가져오기
    df_wx = fetch_open_meteo_daily(lat, lon, start_date, end_date, tz)
    if df_wx is None or df_wx.empty:
        return None, None
    
    # 데이터 병합
    merged = pd.merge(df_trend, df_wx, on="date", how="inner")
    merged["day_type"] = merged.apply(classify_weather, axis=1)
    
    # 요약 통계 생성
    summary = (
        merged.groupby(["group", "day_type"])["ratio"]
        .mean()
        .reset_index()
        .pivot(index="group", columns="day_type", values="ratio")
        .fillna(0.0)
    )
    
    # dry 대비 차이 계산
    for t in ["rain", "snow", "mixed"]:
        if "dry" in summary.columns:
            summary[f"{t}_vs_dry"] = summary.get(t, 0.0) - summary["dry"]
    
    summary = summary.reset_index()
    
    return merged, summary

@st.cache_data
def load_data():
    """기존 CSV 파일에서 데이터 로딩 (백업용)"""
    try:
        # 일별 데이터 로딩
        daily_df = pd.read_csv('naver_golf_trend_weather_daily_2024.csv')
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        # 요약 데이터 로딩
        summary_df = pd.read_csv('naver_golf_trend_weather_summary_2024.csv')
        
        return daily_df, summary_df
    except FileNotFoundError as e:
        st.error(f"데이터 파일을 찾을 수 없습니다: {e}")
        st.info("먼저 golf_weather_naverdatalab_2024.py 스크립트를 실행해주세요.")
        return None, None

def create_weather_metrics(summary_df):
    """날씨별 메트릭 카드 생성"""
    if summary_df is None:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    weather_types = ['dry', 'rain', 'snow', 'mixed']
    weather_names = ['건조', '비', '눈', '혼합']
    weather_colors = ['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A']
    
    for i, (weather, name, color) in enumerate(zip(weather_types, weather_names, weather_colors)):
        with [col1, col2, col3, col4][i]:
            if weather in summary_df.columns:
                avg_ratio = summary_df[weather].mean()
                st.markdown(f"""
                <div class="weather-card {weather}-card">
                    <h3 style="color: {color}; margin: 0;">{name}</h3>
                    <h2 style="margin: 0.5rem 0;">{avg_ratio:.2f}</h2>
                    <p style="margin: 0; font-size: 0.9rem;">평균 검색 비율</p>
                </div>
                """, unsafe_allow_html=True)

def create_trend_chart(daily_df):
    """시계열 트렌드 차트 생성"""
    if daily_df is None:
        return
    
    fig = px.line(
        daily_df, 
        x='date', 
        y='ratio', 
        color='group',
        title='골프 관련 검색 트렌드 (2024년)',
        labels={'ratio': '검색 비율', 'date': '날짜', 'group': '키워드 그룹'}
    )
    
    fig.update_layout(
        height=500,
        xaxis_title="날짜",
        yaxis_title="검색 비율",
        legend_title="키워드 그룹",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_weather_comparison_chart(summary_df):
    """날씨별 비교 차트 생성"""
    if summary_df is None:
        return
    
    # 데이터 준비
    weather_cols = [col for col in ['dry', 'rain', 'snow', 'mixed'] if col in summary_df.columns]
    
    if not weather_cols:
        st.warning("날씨 데이터가 없습니다.")
        return
    
    # 막대 차트 생성
    fig = go.Figure()
    
    colors = {'dry': '#FFA726', 'rain': '#42A5F5', 'snow': '#AB47BC', 'mixed': '#66BB6A'}
    weather_names = {'dry': '건조', 'rain': '비', 'snow': '눈', 'mixed': '혼합'}
    
    for weather in weather_cols:
        fig.add_trace(go.Bar(
            name=weather_names[weather],
            x=summary_df['group'],
            y=summary_df[weather],
            marker_color=colors[weather],
            text=summary_df[weather].round(2),
            textposition='auto'
        ))
    
    fig.update_layout(
        title='키워드별 날씨에 따른 검색 비율 비교',
        xaxis_title='키워드 그룹',
        yaxis_title='평균 검색 비율',
        barmode='group',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_weather_distribution_chart(daily_df):
    """날씨 분포 파이 차트 생성"""
    if daily_df is None:
        return
    
    weather_counts = daily_df['day_type'].value_counts()
    weather_names = {'dry': '건조', 'rain': '비', 'snow': '눈', 'mixed': '혼합'}
    
    fig = px.pie(
        values=weather_counts.values,
        names=[weather_names.get(w, w) for w in weather_counts.index],
        title='2024년 날씨 분포',
        color_discrete_sequence=['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A']
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

def create_correlation_heatmap(daily_df):
    """상관관계 히트맵 생성"""
    if daily_df is None:
        return
    
    # 날씨를 더미 변수로 변환
    weather_dummies = pd.get_dummies(daily_df['day_type'], prefix='weather')
    numeric_df = daily_df[['ratio']].join(weather_dummies)
    
    # 그룹별로 상관관계 계산
    correlation_data = []
    for group in daily_df['group'].unique():
        group_data = numeric_df[daily_df['group'] == group]
        corr = group_data.corr()['ratio'].drop('ratio')
        correlation_data.append({
            'group': group,
            **corr.to_dict()
        })
    
    corr_df = pd.DataFrame(correlation_data).set_index('group')
    
    fig = px.imshow(
        corr_df.T,
        title='키워드 그룹별 날씨와 검색 비율 상관관계',
        color_continuous_scale='RdBu_r',
        aspect='auto'
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def main():
    # 헤더
    st.markdown('<h1 class="main-header">⛳ 골프 날씨 트렌드 대시보드</h1>', unsafe_allow_html=True)
    
    # 사이드바
    st.sidebar.header("🔧 설정")
    
    # 데이터 소스 선택
    data_source = st.sidebar.radio(
        "데이터 소스 선택",
        ["실시간 API 호출", "기존 CSV 파일"],
        help="실시간 API 호출을 선택하면 네이버 데이터랩에서 최신 데이터를 가져옵니다."
    )
    
    if data_source == "실시간 API 호출":
        # API 자격증명 확인
        if not os.environ.get("NAVER_CLIENT_ID") or not os.environ.get("NAVER_CLIENT_SECRET"):
            st.sidebar.error("⚠️ 네이버 API 자격증명이 설정되지 않았습니다.")
            st.sidebar.info("터미널에서 다음 명령어를 실행하세요:")
            st.sidebar.code("""
export NAVER_CLIENT_ID="your_client_id"
export NAVER_CLIENT_SECRET="your_client_secret"
            """)
            st.stop()
        
        # 키워드 입력
        st.sidebar.subheader("🔍 키워드 설정")
        
        # 키워드 그룹 수
        num_groups = st.sidebar.number_input(
            "키워드 그룹 수",
            min_value=1,
            max_value=5,
            value=2,
            help="최대 5개까지 키워드 그룹을 설정할 수 있습니다."
        )
        
        keyword_groups = []
        for i in range(num_groups):
            st.sidebar.write(f"**그룹 {i+1}**")
            group_name = st.sidebar.text_input(
                f"그룹명 {i+1}",
                value=f"그룹{i+1}",
                key=f"group_name_{i}"
            )
            
            keywords_input = st.sidebar.text_input(
                f"키워드 {i+1} (쉼표로 구분)",
                value="골프" if i == 0 else "",
                help="여러 키워드는 쉼표(,)로 구분하세요. 예: 골프, 라운딩",
                key=f"keywords_{i}"
            )
            
            if group_name and keywords_input:
                keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
                if keywords:
                    keyword_groups.append({
                        "groupName": group_name,
                        "keywords": keywords
                    })
        
        if not keyword_groups:
            st.warning("키워드를 입력해주세요.")
            st.stop()
        
        # 날짜 범위 선택
        st.sidebar.subheader("📅 날짜 범위")
        today = date.today()
        start_date = st.sidebar.date_input(
            "시작 날짜",
            value=today - timedelta(days=30),
            max_value=today
        )
        end_date = st.sidebar.date_input(
            "종료 날짜",
            value=today,
            max_value=today
        )
        
        if start_date >= end_date:
            st.error("시작 날짜는 종료 날짜보다 이전이어야 합니다.")
            st.stop()
        
        # 지역 설정
        st.sidebar.subheader("🌍 지역 설정")
        lat = st.sidebar.number_input(
            "위도",
            value=37.5665,
            min_value=-90.0,
            max_value=90.0,
            step=0.0001,
            format="%.4f"
        )
        lon = st.sidebar.number_input(
            "경도",
            value=126.9780,
            min_value=-180.0,
            max_value=180.0,
            step=0.0001,
            format="%.4f"
        )
        
        # 데이터 로딩
        with st.spinner("데이터를 가져오는 중..."):
            daily_df, summary_df = load_data_with_keywords(
                keyword_groups, 
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d"),
                lat, lon
            )
        
        if daily_df is None or summary_df is None:
            st.error("데이터를 가져오는데 실패했습니다. 키워드나 날짜를 확인해주세요.")
            st.stop()
    
    else:  # 기존 CSV 파일 사용
        daily_df, summary_df = load_data()
        
        if daily_df is None or summary_df is None:
            st.stop()
        
        # 키워드 그룹 선택
        selected_groups = st.sidebar.multiselect(
            "키워드 그룹 선택",
            options=daily_df['group'].unique(),
            default=daily_df['group'].unique()
        )
        
        # 날짜 범위 선택
        date_range = st.sidebar.date_input(
            "날짜 범위 선택",
            value=(daily_df['date'].min().date(), daily_df['date'].max().date()),
            min_value=daily_df['date'].min().date(),
            max_value=daily_df['date'].max().date()
        )
        
        # 데이터 필터링
        if selected_groups:
            filtered_daily = daily_df[daily_df['group'].isin(selected_groups)]
        else:
            filtered_daily = daily_df
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_daily = filtered_daily[
                (filtered_daily['date'].dt.date >= start_date) & 
                (filtered_daily['date'].dt.date <= end_date)
            ]
        else:
            filtered_daily = daily_df
    
    # 메인 대시보드
    st.markdown("## 📈 주요 지표")
    create_weather_metrics(summary_df)
    
    st.markdown("## 📊 시계열 트렌드")
    create_trend_chart(daily_df)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("## 🌤️ 날씨별 비교")
        create_weather_comparison_chart(summary_df)
    
    with col2:
        st.markdown("## 📊 날씨 분포")
        create_weather_distribution_chart(daily_df)
    
    st.markdown("## 🔗 상관관계 분석")
    create_correlation_heatmap(daily_df)
    
    # 데이터 테이블
    st.markdown("## 📋 상세 데이터")
    
    # 요약 통계
    st.subheader("요약 통계")
    st.dataframe(summary_df, use_container_width=True)
    
    # 일별 데이터 (샘플)
    st.subheader("일별 데이터 (최근 10일)")
    recent_data = daily_df.nlargest(10, 'date')[['date', 'group', 'ratio', 'day_type', 'precipitation_sum', 'rain_sum', 'snowfall_sum']]
    st.dataframe(recent_data, use_container_width=True)
    
    # 다운로드 버튼
    st.markdown("## 💾 데이터 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_daily = daily_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="일별 데이터 다운로드 (CSV)",
            data=csv_daily,
            file_name=f"golf_weather_daily_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        csv_summary = summary_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="요약 데이터 다운로드 (CSV)",
            data=csv_summary,
            file_name=f"golf_weather_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # 데이터 정보 표시
    st.markdown("---")
    st.markdown("### 📊 데이터 정보")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 데이터 수", f"{len(daily_df):,}개")
    
    with col2:
        st.metric("키워드 그룹 수", f"{len(daily_df['group'].unique())}개")
    
    with col3:
        if not daily_df.empty:
            date_range = f"{daily_df['date'].min().strftime('%Y-%m-%d')} ~ {daily_df['date'].max().strftime('%Y-%m-%d')}"
            st.metric("분석 기간", date_range)

if __name__ == "__main__":
    main()

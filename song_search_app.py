import pandas as pd
import streamlit as st
from datetime import datetime
import os
import pypinyin

# 设置页面
st.set_page_config(page_title="歌曲演唱记录查询系统", layout="wide")
st.title("🎵 歌曲演唱记录查询系统")

# GitHub raw文件URL（直接使用你的文件路径）
GITHUB_RAW_URL ="https://github.com/Jellymemory/ChurchSongSearch/raw/refs/heads/main/Weekly%20Report%20Data%20Extracted_processed_08092025_FINAL.xlsx"

# 加载数据
@st.cache_data(ttl=3600)  # 缓存1小时
def load_data():
    try:
        # 直接从GitHub raw读取Excel文件
        df = pd.read_excel(GITHUB_RAW_URL, engine='openpyxl')
        
        # 重命名列
        df = df.rename(columns={
            'Year': 'Year',
            'Month': 'Month',
            'Day': 'Day',
            'Simplified Chinese': 'Simplified',
            'Traditional Chinese': 'Traditional'
        })
        
        # 合并年月日创建日期列
        df['演唱日期'] = pd.to_datetime(
            df['Year'].astype(str) + '-' + 
            df['Month'].astype(str) + '-' + 
            df['Day'].astype(str),
            format='%Y-%m-%d',
            errors='coerce'
        )
        
        # 移除无效日期
        df = df.dropna(subset=['演唱日期'])
        
        # 筛选最近5年的数据
        current_year = datetime.now().year
        df = df[df['演唱日期'].dt.year >= (current_year - 5)]
        
        return df
    except Exception as e:
        st.error(f"加载数据失败: {str(e)}")
        return pd.DataFrame()

# 获取拼音首字母用于排序
def get_pinyin_initial(text):
    try:
        initials = pypinyin.lazy_pinyin(text, style=pypinyin.Style.FIRST_LETTER)
        return ''.join(initials).lower()
    except:
        return ''

df = load_data()

# 检查数据是否加载成功
if df.empty:
    st.stop()

# 搜索功能
def search_songs(search_term):
    try:
        # 同时在简体和繁体列中搜索
        simplified_matches = df[df['Simplified'].str.contains(search_term, case=False, na=False, regex=False)]
        traditional_matches = df[df['Traditional'].str.contains(search_term, case=False, na=False, regex=False)]
        
        # 合并结果并去重
        all_matches = pd.concat([simplified_matches, traditional_matches]).drop_duplicates()
        return all_matches
    except:
        return pd.DataFrame()

# 自动完成功能
def get_autocomplete_suggestions(partial_term):
    try:
        # 获取简体和繁体中部分匹配的歌曲名
        simplified_suggestions = df[df['Simplified'].str.contains(partial_term, case=False, na=False)]['Simplified'].dropna().unique()
        traditional_suggestions = df[df['Traditional'].str.contains(partial_term, case=False, na=False)]['Traditional'].dropna().unique()
        
        # 合并建议并去重
        suggestions = list(set(list(simplified_suggestions) + list(traditional_suggestions)))
        return suggestions[:10]  # 限制返回10条建议
    except:
        return []

# 用户界面
search_term = st.text_input("请输入歌曲名称 (支持简体和繁体中文):", 
                           key="search",
                           help="输入部分歌名可获取自动提示")

# 自动完成建议
if search_term and len(search_term) >= 1:
    with st.spinner('正在搜索...'):
        suggestions = get_autocomplete_suggestions(search_term)
        if suggestions:
            st.write("相关歌名:")
            cols = st.columns(2)  # 创建2列显示建议
            for i, song in enumerate(suggestions):
                with cols[i % 2]:  # 交替分配到两列
                    if st.button(song, key=f"suggest_{song}"):
                        st.session_state['selected_song'] = song
                        st.rerun()  # 重新运行以更新结果

# 如果从建议中选择歌曲，使用session_state中的值
if 'selected_song' in st.session_state:
    search_term = st.session_state['selected_song']
    del st.session_state['selected_song']

# 执行搜索
if search_term:
    with st.spinner('正在查询...'):
        results = search_songs(search_term)
        
        if not results.empty:
            # 获取所有匹配的歌曲名(简体和繁体)
            unique_songs = pd.concat([results['Simplified'], results['Traditional']]).dropna().unique()
            
            # 让用户选择具体歌曲(如果有多个匹配)
            if len(unique_songs) > 1:
                selected_song = st.selectbox("找到多个匹配歌曲，请选择:", unique_songs)
                
                # 确定要搜索的是简体还是繁体列
                if selected_song in results['Simplified'].values:
                    song_data = results[results['Simplified'] == selected_song]
                else:
                    song_data = results[results['Traditional'] == selected_song]
            else:
                song_data = results
                selected_song = unique_songs[0]
            
            # 显示结果
            st.success(f"🎤 歌曲: {selected_song}")
            
            # 统计演唱次数
            performance_count = len(song_data)
            st.metric("在过去5年演唱次数", performance_count)
            
            # 显示日期列表
            st.subheader("演唱日期列表")
            dates = song_data.sort_values('演唱日期', ascending=False)['演唱日期']
            st.table(dates.dt.strftime('%Y年%m月%d日').to_frame(name="日期"))
            
            # 下载按钮
            csv = song_data[['Simplified', 'Traditional', '演唱日期']].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "下载查询结果",
                csv,
                f"{selected_song}_演唱记录.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.warning("抱歉，您搜索的歌名过去5年没有被演唱。")

# 侧边栏显示统计数据
with st.sidebar:
    st.header("统计数据")
    st.write(f"数据集包含 {len(df)} 条演唱记录")
    st.write(f"涵盖 {len(df['Simplified'].dropna().unique())} 首不同歌曲")
    
    
    # 显示所有歌曲并按需排序
    st.subheader("所有歌曲演唱统计(简体)")
    
    # 创建排序选项
    sort_option = st.radio("排序方式:", 
                         ["按演唱次数降序", "按歌曲名(A-Z)"],
                         index=0)
    
    # 获取所有歌曲统计数据
    song_stats = df['Simplified'].value_counts().reset_index()
    song_stats.columns = ['歌曲名', '演唱次数']  # 正确设置列名
    
    # 添加拼音首字母列用于排序
    song_stats['拼音首字母'] = song_stats['歌曲名'].apply(get_pinyin_initial)
    
    # 根据选择排序
    if sort_option == "按演唱次数降序":
        song_stats = song_stats.sort_values('演唱次数', ascending=False)
    else:
        song_stats = song_stats.sort_values('拼音首字母', ascending=True)
    
    # 显示表格（使用st.dataframe实现可排序）
    st.dataframe(
        song_stats[['歌曲名', '演唱次数']],  # 不显示拼音首字母列
        height=600,
        use_container_width=True,
        column_config={
            "歌曲名": st.column_config.TextColumn("歌曲名"),
            "演唱次数": st.column_config.NumberColumn("演唱次数")
        }
    )


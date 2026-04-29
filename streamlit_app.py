import streamlit as st
import pandas as pd
import plotly.express as px
import io

# 1. 页面基本设置 (使用宽屏模式)
st.set_page_config(page_title="宝可梦卡牌市场分析大屏", page_icon="🐉", layout="wide")

# 自定义 CSS 让页面更好看
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6; /* 浅色背景 */
        color: #1f1f1f;           /* 强制主体文字为深色 */
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card h4, .metric-card h2 {
        color: #1f1f1f !important; /* 强制标题和数字为深色 */
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

st.title(" 闲鱼宝可梦卡牌市场深度分析")
st.markdown("基于抓取的闲鱼交易数据，为您提供多维度的卡牌价格洞察。")

# 2. 读取数据 (开启缓存)
@st.cache_data
def load_data():
    # 假设你的数据文件名是这个，如果有变请修改
    df = pd.read_excel('闲鱼清洗后宝可梦数据.xlsx')
    # 处理一些可能存在的异常价格（比如价格为0或极高的脏数据）
    df = df[df['价格'] > 0] 
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"读取数据失败，请确保 '闲鱼清洗后宝可梦数据.xlsx' 文件在当前目录下。错误详情：{e}")
    st.stop()

# 3. 侧边栏：全局过滤器
st.sidebar.header(" 核心筛选器")

# 提取唯一值 (优化了提取逻辑，更严谨)
def get_unique_list(column_name):
    unique_set = set()
    for items in df[column_name].dropna():
        for item in str(items).split(' '):
            if item and item not in ['非宝可梦', '其他版本', '无评级', '无评分']:
                unique_set.add(item)
    return sorted(list(unique_set))

all_roles = ["全部"] + get_unique_list('包含角色')
all_versions = ["全部"] + get_unique_list('卡牌版本')
all_grades = ["全部"] + get_unique_list('评级方式')

# 交互组件
selected_role = st.sidebar.selectbox(" 选择核心角色", all_roles)
selected_version = st.sidebar.selectbox(" 选择卡牌版本", all_versions)
selected_grade = st.sidebar.selectbox("选择评级公司", all_grades)

# 价格双向滑块
min_price, max_price = int(df['价格'].min()), int(df['价格'].max())
selected_price = st.sidebar.slider("价格区间 (元)", min_price, max_price, (min_price, max_price))

# 4. 执行过滤
filtered_df = df.copy()

if selected_role != "全部":
    filtered_df = filtered_df[filtered_df['包含角色'].str.contains(selected_role, na=False)]
if selected_version != "全部":
    filtered_df = filtered_df[filtered_df['卡牌版本'].str.contains(selected_version, na=False)]
if selected_grade != "全部":
    filtered_df = filtered_df[filtered_df['评级方式'].str.contains(selected_grade, na=False)]

filtered_df = filtered_df[(filtered_df['价格'] >= selected_price[0]) & (filtered_df['价格'] <= selected_price[1])]

# 5. 顶部核心指标 KPI (使用自定义 HTML 卡片)
if len(filtered_df) > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"<div class='metric-card'><h4>有效样本数</h4><h2>{len(filtered_df)} 张</h2></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-card'><h4>市场均价</h4><h2>¥ {filtered_df['价格'].mean():,.0f}</h2></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-card'><h4>最高成交价</h4><h2>¥ {filtered_df['价格'].max():,.0f}</h2></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='metric-card'><h4>价格中位数</h4><h2>¥ {filtered_df['价格'].median():,.0f}</h2></div>", unsafe_allow_html=True)
else:
    st.warning(" 当前筛选条件下没有数据，请调整侧边栏的筛选范围。")

st.markdown("---")

# 6. 数据可视化区 (使用 Plotly 提供高级交互)

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["角色溢价排行", "分数与价格散点图", "原始数据探查"])

with tab1:
    st.subheader("不同角色的市场吸金能力 (Top 15)")
    
    # 后台数据炸开处理
    df_chart = filtered_df.copy()
    df_chart['单角色'] = df_chart['包含角色'].astype(str).str.split(' ')
    df_chart = df_chart.explode('单角色')
    df_chart = df_chart[(df_chart['单角色'] != '') & (df_chart['单角色'] != '非宝可梦')]
    
    if not df_chart.empty:
        # 计算均价并重置索引以便画图
        price_by_role = df_chart.groupby('单角色', as_index=False)['价格'].mean()
        price_by_role = price_by_role.sort_values(by='价格', ascending=False).head(15)
        
        # 使用 Plotly 画交互式柱状图
        fig1 = px.bar(price_by_role, x='单角色', y='价格', 
                      title="平均溢价排行榜", 
                      text_auto='.0f',
                      color='价格', color_continuous_scale='Reds')
        fig1.update_layout(xaxis_title="角色", yaxis_title="平均价格 (元)")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("暂无足够的角色数据进行排行。")

with tab2:
    st.subheader("评级分数对价格的拉升作用")
    st.markdown("每一个点代表一张实际卡片。可以直观看到高分卡是否显著溢价。")
    
    # 过滤掉没有评分的脏数据
    df_scatter = filtered_df[filtered_df['评分'] != '无评分'].copy()
    
    if not df_scatter.empty:
        # 确保评分列是数字格式
        df_scatter['评分数值'] = pd.to_numeric(df_scatter['评分'], errors='coerce')
        df_scatter = df_scatter.dropna(subset=['评分数值'])
        
        # 使用 Plotly 画散点图
        fig2 = px.scatter(df_scatter, x='评分数值', y='价格', 
                          color='卡牌版本' if selected_version == "全部" else '评级方式',
                          hover_data=['包含角色', '卡牌版本', '评级方式'],
                          title="分数 vs 价格 分布",
                          opacity=0.7)
        # 添加趋势线 (需要安装 statsmodels 库: pip install statsmodels)
        try:
             fig2.update_traces(marker=dict(size=10))
        except:
             pass
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("当前筛选条件下缺少带有明确数字评分的卡片数据。")

with tab3:
    st.subheader("明细数据流")
    
    # 定义展示列
    display_cols = ['价格', '包含角色', '卡牌版本', '评级方式', '评分']
    # 如果有标题列，最好展示标题
    if '标题' in df.columns:
        display_cols.insert(1, '标题')
        
    st.dataframe(filtered_df[display_cols], use_container_width=True, height=400)
    
    # 一键下载功能
    csv = filtered_df[display_cols].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="下载当前筛选数据为 CSV",
        data=csv,
        file_name='pokemon_cards_filtered.csv',
        mime='text/csv',
    )

# 侧边栏底部版权信息
st.sidebar.markdown("---")
st.sidebar.markdown("**提示**：在图表区域，您可以按住鼠标拖动进行缩放，悬停查看具体数值。")

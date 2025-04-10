import pandas as pd
import zipfile
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import requests
from io import BytesIO
import streamlit as st

## LOAD DATA DIRECTLY FROM SSA WEBSITE
@st.cache_data
def load_name_data():
    names_file = 'https://www.ssa.gov/oact/babynames/names.zip'
    response = requests.get(names_file)
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        dfs = []
        # Get all text files inside the zip (each represents a year)
        files = [file for file in z.namelist() if file.endswith('.txt')]
        for file in files:
            with z.open(file) as f:
                df = pd.read_csv(f, header=None)
                df.columns = ['name', 'sex', 'count']
                df['year'] = int(file[3:7])
                dfs.append(df)
        data = pd.concat(dfs, ignore_index=True)
    data['pct'] = data['count'] / data.groupby(['year', 'sex'])['count'].transform('sum')
    data['total_births'] = data.groupby(['year', 'sex'])['count'].transform('sum')
    data['prop'] = data['count'] / data['total_births']
    return data

# Load the dataset
df = load_name_data()

# -------------------------------
# APP TITLE & SIDEBAR WIDGETS
# -------------------------------
st.title('Social Security National Names Analysis')

# Sidebar for filter inputs
st.sidebar.title("Filters")
# 1. Text input: name to search
name_input = st.sidebar.text_input("Enter a name to search")
# 2. Checkbox inputs: choose which gender line(s) to plot for the trend analysis
plot_female = st.sidebar.checkbox("Plot Female Trend", value=True)
plot_male = st.sidebar.checkbox("Plot Male Trend", value=True)
# 3. Slider: select the range of years
year_range = st.sidebar.slider("Select Year Range", 1880, 2022, (1880, 2022))
# 4. Selectbox: choose which gender to use for data summary
summary_gender = st.sidebar.selectbox("Select Gender for Summary", options=["Both", "F", "M"])

# Filter the main dataframe based on the selected year range
filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

# -------------------------------
# MAIN AREA: TWO TABS
# -------------------------------
tab1, tab2 = st.tabs(["Trend Analysis", "Data Summary & Visualization"])

# ----- TAB 1: Trend Analysis -----
with tab1:
    st.header("Trend Analysis")
    # Dynamic text output that updates based on the text input and year slider
    if name_input:
        st.write(f"Showing trend for **{name_input}** from **{year_range[0]}** to **{year_range[1]}**")
        # Use a case-insensitive match for the name
        name_df = filtered_df[filtered_df['name'].str.lower() == name_input.lower()]
    else:
        st.write("Please enter a name in the sidebar to see its trend.")
        name_df = pd.DataFrame()  # empty dataframe when no name provided

    # Plot the trend using matplotlib and seaborn if data exists and at least one checkbox is selected
    if not name_df.empty and (plot_female or plot_male):
        fig, ax = plt.subplots(figsize=(10, 6))
        # Plot female trend if checkbox is checked
        if plot_female:
            df_f = name_df[name_df['sex'] == 'F']
            if not df_f.empty:
                sns.lineplot(data=df_f, x='year', y='prop', label='Female', ax=ax)
        # Plot male trend if checkbox is checked
        if plot_male:
            df_m = name_df[name_df['sex'] == 'M']
            if not df_m.empty:
                sns.lineplot(data=df_m, x='year', y='prop', label='Male', ax=ax)
        ax.set_title(f"Popularity of '{name_input}' over time")
        ax.set_xlabel("Year")
        ax.set_ylabel("Proportion")
        ax.set_xlim(year_range)
        ax.legend()
        st.pyplot(fig)
    else:
        st.write("No data available for the selected name and filters.")

# ----- TAB 2: Data Summary & Visualization -----
with tab2:
    st.header("Data Summary & Visualization")
    # Using a container to group summary statistics
    with st.container():
        st.subheader("Summary Statistics")
        # Based on the selected gender for the summary, filter and compute totals
        if summary_gender == "Both":
            total_births = filtered_df['count'].sum()
            summary_df = filtered_df.groupby('name')['count'].sum().reset_index()
        else:
            gender_df = filtered_df[filtered_df['sex'] == summary_gender]
            total_births = gender_df['count'].sum()
            summary_df = gender_df.groupby('name')['count'].sum().reset_index()
        # Sort names by count and take the top 10
        summary_df = summary_df.sort_values(by='count', ascending=False).head(10)
        
        st.write(f"**Total births** in the selected range: **{total_births:,}**")
        st.dataframe(summary_df)

    st.subheader("Top 10 Names Bar Chart")
    # Create a bar chart for the top 10 names using Plotly Express if data is available
    if not summary_df.empty:
        bar_fig = px.bar(summary_df, x='name', y='count', title="Top 10 Names")
        st.plotly_chart(bar_fig)
    else:
        st.write("No data available for the selected filters.")

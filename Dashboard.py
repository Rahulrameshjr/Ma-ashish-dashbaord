import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="MAA ASHISH – Production Intelligence",
    layout="wide"
)

# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_data():
    file = "MAA_AASHISH_Production_Data_v2.xlsx"

    machine = pd.read_excel(file, sheet_name="Machine & Production")
    operator = pd.read_excel(file, sheet_name="Operator Details")

    # Normalize column names
    machine.columns = machine.columns.str.strip().str.title()
    operator.columns = operator.columns.str.strip().str.title()

    for df in [machine, operator]:
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month
        df["Month_Name"] = df["Date"].dt.strftime("%B")

    return machine, operator


machine_df, operator_df = load_data()

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.title("🔍 Filters")

year_sel = st.sidebar.multiselect(
    "Year",
    sorted(machine_df["Year"].unique()),
    default=sorted(machine_df["Year"].unique())
)

month_sel = st.sidebar.multiselect(
    "Month",
    sorted(machine_df["Month_Name"].unique())
)

date_range = st.sidebar.date_input("Date Range", [])

# ----------------------------
# FILTER FUNCTION (FIXED)
# ----------------------------
def apply_filters(df):
    df = df.copy()

    # Highest priority → Date range
    if len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df = df[(df["Date"] >= start) & (df["Date"] <= end)]

    else:
        if year_sel:
            df = df[df["Year"].isin(year_sel)]

        if month_sel:
            df = df[df["Month_Name"].isin(month_sel)]

    return df


machine_f = apply_filters(machine_df)
operator_f = apply_filters(operator_df)

# ----------------------------
# EMPTY DATA GUARD
# ----------------------------
if machine_f.empty:
    st.warning("⚠️ No data available for selected filters")
    st.stop()

# ----------------------------
# HEADER
# ----------------------------
st.title("🧶 MAA ASHISH – Production Intelligence Dashboard")

# ----------------------------
# TABS
# ----------------------------
tab_machine, tab_prod, tab_operator = st.tabs(
    ["⚙️ Machine Dashboard", "📊 Production Dashboard", "👷 Operator Efficiency"]
)

# ==================================================
# ⚙️ MACHINE DASHBOARD
# ==================================================
with tab_machine:

    st.subheader("⚙️ Machine Performance Overview")

    # Efficiency Calculation
    machine_eff = machine_f.copy()
    machine_eff["Efficiency %"] = (
        machine_eff["Actual Counter"] / machine_eff["100% Efficiency"]
    ) * 100

    # Top N Machines
    top_n = st.number_input(
        "Show Top N Efficient Machines",
        min_value=1,
        max_value=20,
        value=5
    )

    top_machines = (
        machine_eff
        .groupby("Machine Number")
        .agg(
            Avg_Efficiency=("Efficiency %", "mean"),
            Total_Rolls=("Production", "sum")
        )
        .reset_index()
        .sort_values("Avg_Efficiency", ascending=False)
        .head(top_n)
    )

    # Ensure categorical x-axis
    top_machines["Machine Number"] = top_machines["Machine Number"].astype(str)

    fig = px.bar(
        top_machines,
        x="Machine Number",
        y="Avg_Efficiency",
        text=top_machines["Avg_Efficiency"].round(1).astype(str) + "%",
        title="Top Efficient Machines",
        category_orders={
            "Machine Number": top_machines["Machine Number"].tolist()
        }
    )

    fig.update_traces(textposition="outside")

    fig.update_yaxes(
        title="Efficiency (%)",
        range=[0, 100]
    )

    fig.update_xaxes(
        title="Machine Number",
        type="category"
    )

    fig.update_xaxes(title="Efficiency (%)")
    st.plotly_chart(fig, use_container_width=True)

    # Rolls by Machine
    st.subheader("📦 Rolls Produced by Machine")

    # Aggregate production by machine
    rolls_by_machine = (
        machine_f
        .groupby("Machine Number")["Production"]
        .sum()
        .reset_index()
        .sort_values("Machine Number")
    )

    # 🔑 Convert Machine Number to string for categorical axis
    rolls_by_machine["Machine Number"] = rolls_by_machine["Machine Number"].astype(str)

    fig = px.line(
        rolls_by_machine,
        x="Machine Number",
        y="Production",
        markers=True
    )

    fig.update_layout(
        xaxis_title="Machine Number",
        yaxis_title="Total Rolls Produced",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=rolls_by_machine["Machine Number"].tolist()
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # ==================================================
    # 🔎 MACHINE-WISE SUMMARY TABLE (COMBINED VIEW)
    # ==================================================

    st.subheader("🔎 Machine-wise Performance Summary")

    # Aggregate machine data for selected filters
    machine_summary = (
        machine_f
        .groupby("Machine Number")
        .agg(
            Avg_Rpm=("Rpm", "mean"),
            Total_100_Efficiency=("100% Efficiency", "sum"),
            Total_Actual_Counter=("Actual Counter", "sum"),
            Total_Production_Rolls=("Production", "sum")
        )
        .reset_index()
    )

    # Calculate efficiency %
    machine_summary["Efficiency %"] = (
        machine_summary["Total_Actual_Counter"] /
        machine_summary["Total_100_Efficiency"]
    ) * 100

    # Formatting
    machine_summary["Avg_Rpm"] = machine_summary["Avg_Rpm"].round(1)
    machine_summary["Efficiency %"] = machine_summary["Efficiency %"].round(2)

    # Optional: Machine number filter (typed input)
    machine_input = st.text_input(
    "Enter Machine Number (leave empty to view all)",
    placeholder="e.g. 1"
    )

    # Apply filter ONLY if input is provided
    if machine_input.strip().isdigit():
        machine_summary_view = machine_summary[
            machine_summary["Machine Number"] == int(machine_input)
        ]
    else:
        machine_summary_view = machine_summary.copy()

    # Display table
    st.data_editor(
        machine_summary_view,
        use_container_width=True,
        hide_index=True,
        disabled=True
    )


# ==================================================
# 📊 PRODUCTION DASHBOARD
# ==================================================
with tab_prod:

    st.subheader("📊 Production Overview")

    total_rolls = machine_f["Production"].sum()
    avg_daily = machine_f.groupby("Date")["Production"].sum().mean()

    c1, c2 = st.columns(2)
    c1.metric("Total Rolls Produced", f"{total_rolls:,.0f}")
    c2.metric("Avg Daily Rolls", f"{avg_daily:.1f}")

    # Production Trend
    prod_trend = (
        machine_f
        .groupby("Date")["Production"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        prod_trend,
        x="Date",
        y="Production",
        markers=True,
        title="Daily Production Trend (Rolls)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Total Rolls Produced (Smart View)")

    prod_df = machine_f.copy()

    # ----------------------------
    # ENSURE WEEK COLUMN EXISTS
    # ----------------------------
    if "Week" not in prod_df.columns:
        prod_df["Week"] = prod_df["Date"].dt.isocalendar().week.astype(int)

    # ----------------------------
    # DETECT AGGREGATION LEVEL
    # ----------------------------
    if len(date_range) == 2:
        aggregation = "date"
    elif month_sel:
        if len(month_sel) == 1:
            aggregation = "week"
        else:
            aggregation = "month"
    else:
        aggregation = "month"

    # ----------------------------
    # AGGREGATE DATA
    # ----------------------------
    if aggregation == "date":

        grouped = (
            prod_df
            .groupby("Date")["Production"]
            .sum()
            .reset_index()
            .sort_values("Date")
        )

        grouped["Label"] = grouped["Date"].dt.strftime("%Y-%m-%d")
        title = "Total Rolls Produced (Date-wise)"

    elif aggregation == "week":

        grouped = (
            prod_df
            .groupby(["Year", "Week"])["Production"]
            .sum()
            .reset_index()
            .sort_values(["Year", "Week"])
        )

        grouped["Label"] = "Week " + grouped["Week"].astype(str)
        title = "Total Rolls Produced (Week-wise)"

    else:  # MONTH-WISE

        grouped = (
            prod_df
            .groupby(["Year", "Month", "Month_Name"])["Production"]
            .sum()
            .reset_index()
            .sort_values(["Year", "Month"])
        )

        grouped["Label"] = grouped["Month_Name"] + " " + grouped["Year"].astype(str)
        title = "Total Rolls Produced (Month-wise)"

    # ----------------------------
    # FORCE CATEGORICAL AXIS
    # ----------------------------
    grouped["Label"] = grouped["Label"].astype(str)

    # ----------------------------
    # BAR CHART
    # ----------------------------
    fig = px.bar(
        grouped,
        x="Label",
        y="Production",
        text_auto=True
    )

    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title="Total Rolls Produced",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=grouped["Label"].tolist()
        )
    )

    st.plotly_chart(fig, use_container_width=True)




    # Table View
    st.subheader("📋 Production Table")

    view_type = st.selectbox(
        "View By",
        ["Machine-wise", "Date-wise"]
    )

    if view_type == "Machine-wise":
        table = (
            machine_f
            .groupby("Machine Number")["Production"]
            .sum()
            .reset_index()
        )
    else:
        table = (
            machine_f
            .groupby("Date")["Production"]
            .sum()
            .reset_index()
        )

    st.data_editor(
        table,
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

# ==================================================
# 👷 OPERATOR EFFICIENCY DASHBOARD
# ==================================================

with tab_operator:

    st.subheader("👷 Operator Efficiency Overview")

    # ----------------------------
    # AGGREGATE OPERATOR DATA
    # ----------------------------
    operator_summary = (
        operator_f
        .groupby("Machine Operator")["Production"]
        .sum()
        .reset_index()
        .sort_values("Production", ascending=False)
    )

    # Safety check
    if operator_summary.empty:
        st.warning("No operator data available for selected filters")
        st.stop()

    # ==================================================
    # 🏆 TOP N OPERATORS
    # ==================================================
    st.subheader("🏆 Top Performing Operators")

    top_n_ops = st.number_input(
        "Show Top N Operators",
        min_value=1,
        max_value=len(operator_summary),
        value=5,
        step=1
    )

    top_ops = operator_summary.head(top_n_ops)

    fig = px.bar(
        top_ops,
        x="Production",
        y="Machine Operator",
        orientation="h",
        text_auto=True
    )

    fig.update_layout(
        title="Top Operators by Total Production",
        xaxis_title="Total Production",
        yaxis_title="Operator",
        yaxis=dict(categoryorder="total ascending")
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ==================================================
    # ⚠️ BOTTOM N OPERATORS
    # ==================================================
    st.subheader("⚠️ Bottom Performing Operators")

    bottom_n_ops = st.number_input(
        "Show Bottom N Operators",
        min_value=1,
        max_value=len(operator_summary),
        value=5,
        step=1,
        key="bottom_ops"
    )

    bottom_ops = operator_summary.tail(bottom_n_ops)

    fig = px.bar(
        bottom_ops,
        x="Production",
        y="Machine Operator",
        orientation="h",
        text_auto=True
    )

    fig.update_layout(
        title="Bottom Operators by Total Production",
        xaxis_title="Total Production",
        yaxis_title="Operator",
        yaxis=dict(categoryorder="total descending")
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Shift Comparison
    shift_prod = (
        operator_f
        .groupby("Shift (Day/Night)")["Production"]
        .sum()
        .reset_index()
    )

    fig = px.pie(
        shift_prod,
        values="Production",
        names="Shift (Day/Night)",
        title="Day vs Night Shift Production"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ==================================================
    # 👷 OPERATOR DETAILS – COMBINED VIEW ONLY
    # ==================================================

    st.subheader("👷 Operator Performance Summary")

    # ----------------------------
    # OPERATOR PRODUCTION
    # ----------------------------
    operator_prod = (
        operator_f
        .groupby("Machine Operator")["Production"]
        .sum()
        .reset_index()
    )

    # ----------------------------
    # MACHINES HANDLED
    # ----------------------------
    operator_machines = (
        operator_f
        .groupby("Machine Operator")["Machine Number"]
        .unique()
        .reset_index()
    )

    operator_machines["Machines Handled"] = operator_machines["Machine Number"].apply(
        lambda x: ", ".join(map(str, sorted(x)))
    )

    operator_machines.drop(columns=["Machine Number"], inplace=True)

    # ----------------------------
    # OPERATOR EFFICIENCY
    # ----------------------------
    op_machine_merge = operator_f.merge(
        machine_f,
        on=["Date", "Machine Number"],
        how="left"
    )

    operator_eff = (
        op_machine_merge
        .groupby("Machine Operator")
        .agg(
            Total_Actual=("Actual Counter", "sum"),
            Total_Max=("100% Efficiency", "sum")
        )
        .reset_index()
    )

    operator_eff["Efficiency %"] = (
        operator_eff["Total_Actual"] / operator_eff["Total_Max"]
    ) * 100

    operator_eff["Efficiency %"] = operator_eff["Efficiency %"].round(2)

    # ----------------------------
    # FINAL OPERATOR SUMMARY
    # ----------------------------
    operator_summary = (
        operator_prod
        .merge(operator_machines, on="Machine Operator")
        .merge(operator_eff[["Machine Operator", "Efficiency %"]], on="Machine Operator")
    )

    # ----------------------------
    # OPERATOR SELECTOR
    # ----------------------------
    selected_operator = st.selectbox(
        "Select Operator (optional)",
        options=["All"] + sorted(operator_summary["Machine Operator"].unique())
    )

    # ----------------------------
    # DISPLAY LOGIC
    # ----------------------------
    if selected_operator == "All":
        display_df = operator_summary.sort_values("Production", ascending=False)
    else:
        display_df = operator_summary[
            operator_summary["Machine Operator"] == selected_operator
        ]

    # ----------------------------
    # DISPLAY TABLE
    # ----------------------------
    st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

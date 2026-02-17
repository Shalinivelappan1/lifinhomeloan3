import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — Classroom NPV Simulator")
st.caption("Developer: Dr. Shalini Velappan")

tab1, tab2 = st.tabs(["Simulator", "Student Guide"])

# =====================================================
# SIMULATOR
# =====================================================
with tab1:

    # ---------- INPUTS ----------
    st.sidebar.header("Property")

    price = st.sidebar.number_input("House price", value=1500000.0)
    down_pct = st.sidebar.number_input("Down payment %", value=20.0)
    loan_rate = st.sidebar.number_input("Loan interest %", value=3.0)
    tenure = st.sidebar.number_input("Loan tenure (years)", value=30)

    st.sidebar.header("Rent")
    rent0 = st.sidebar.number_input("Monthly rent", value=4000.0)
    rent_growth = st.sidebar.number_input("Rent growth %", value=2.0)

    st.sidebar.header("Market")
    house_growth = st.sidebar.number_input("House price growth %", value=3.0)
    disc = st.sidebar.number_input("Discount / investment return %", value=5.0)

    st.sidebar.header("Holding period")

    lifetime = st.sidebar.checkbox("Hold till lifetime (no sale)")
    if lifetime:
        exit_year = 60
    else:
        exit_year = st.sidebar.number_input(
            "Sell after years", min_value=1, value=10
        )

    st.sidebar.header("Costs")
    buy_commission = st.sidebar.number_input("Buy commission %", value=1.0)
    sell_commission = st.sidebar.number_input("Sell commission %", value=1.0)
    monthly_costs = st.sidebar.number_input(
        "Maintenance + tax + repairs (monthly)", value=450.0
    )

    # ---------- TAX ----------
    st.sidebar.header("India tax benefits")
    use_tax = st.sidebar.checkbox("Apply home-loan tax deductions (80C + Sec24)", value=True)

    tax_rate = 0.30
    interest_cap = 200000
    principal_cap = 150000

    # ---------- EMI ----------
    downpayment = price * down_pct/100
    loan_amt = price - downpayment

    r = loan_rate/100/12
    n = tenure*12

    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)
    st.metric("Monthly EMI", f"{emi:,.2f}")

    # ---------- TEACHING: YEAR 1 BREAKDOWN ----------
    year1_interest = 0
    year1_principal = 0
    bal = loan_amt

    for m in range(12):
        i = bal*r
        p = emi - i
        bal -= p
        year1_interest += i
        year1_principal += p

    st.info(
        f"Year-1 interest: {year1_interest:,.0f} | "
        f"principal repaid: {year1_principal:,.0f}"
    )

    # =====================================================
    # NPV FUNCTION
    # =====================================================
    def compute_npv(hg, rg, tax_on=True):

        months = int(exit_year*12)
        monthly_disc = disc/100/12

        # ---------- BUY ----------
        cf_buy = []

        initial = downpayment + price*buy_commission/100 + 0.03*price + 8000
        cf_buy.append(-initial)

        balance = loan_amt

        for m in range(1, months+1):

            interest = balance*r
            principal = emi - interest
            balance -= principal

            tax_saving_monthly = 0

            if tax_on:
                annual_interest = interest * 12
                annual_principal = principal * 12

                interest_ded = min(annual_interest, interest_cap)
                principal_ded = min(annual_principal, principal_cap)

                tax_saving_monthly = (
                    (interest_ded + principal_ded) * tax_rate / 12
                )

            cf_buy.append(-(emi + monthly_costs - tax_saving_monthly))

        if not lifetime:
            sale_price = price*(1+hg/100)**exit_year
            sale_net = sale_price*(1-sell_commission/100) - balance
            cf_buy[-1] += sale_net

        # ---------- RENT ----------
        cf_rent = []

        invest0 = downpayment + price*buy_commission/100 + 0.03*price + 8000
        cf_rent.append(-invest0)

        rent = rent0
        invest_balance = invest0

        for m in range(1, months+1):

            invest_balance *= (1 + monthly_disc)
            rent = rent*(1 + rg/100/12)

            cf_rent.append(-rent)

        cf_rent[-1] += invest_balance

        def npv(rate, cfs):
            return sum(cf/((1+rate)**i) for i, cf in enumerate(cfs))

        return npv(monthly_disc, cf_buy), npv(monthly_disc, cf_rent)

    # =====================================================
    # SCENARIOS
    # =====================================================
    st.subheader("Scenario comparison")

    rows=[]
    for name,(hg,rg) in {
        "Base": (house_growth, rent_growth),
        "Boom": (house_growth+1, rent_growth),
        "Crash": (house_growth-1, rent_growth)
    }.items():

        b,rn = compute_npv(hg,rg,use_tax)
        rows.append([name,b,rn,b-rn])

    df = pd.DataFrame(rows,
        columns=["Scenario","NPV Buy","NPV Rent","Buy-Rent"]
    )
    st.dataframe(df, use_container_width=True)

    # =====================================================
    # SENSITIVITY
    # =====================================================
    st.subheader("Growth sensitivity")

    g = st.slider("House price growth %", -5.0, 8.0, float(house_growth))
    b,rn = compute_npv(g, rent_growth, use_tax)

    col1,col2,col3 = st.columns(3)
    col1.metric("NPV Buy", f"{b:,.0f}")
    col2.metric("NPV Rent", f"{rn:,.0f}")
    col3.metric("Buy advantage (₹)", f"{b-rn:,.0f}")

    # =====================================================
    # BREAK-EVEN CHART
    # =====================================================
    st.subheader("Break-even house growth")

    growths = np.linspace(-5,8,80)
    diffs=[]

    for gr in growths:
        b,rn = compute_npv(gr, rent_growth, use_tax)
        diffs.append(b-rn)

    fig = go.Figure()

    fig.add_scatter(
        x=growths,
        y=diffs,
        mode="lines",
        line=dict(width=5, color="blue")
    )

    fig.add_hline(y=0, line_width=4, line_color="black")

    break_even=None
    for i in range(len(diffs)-1):
        if diffs[i]*diffs[i+1] < 0:
            break_even = growths[i]
            break

    if break_even:
        fig.add_vline(x=break_even, line_dash="dash", line_color="red", line_width=3)
        fig.add_annotation(
            x=break_even,
            y=max(diffs)*0.8,
            text=f"Break-even ≈ {break_even:.2f}%",
            font=dict(size=20, color="red"),
            showarrow=True
        )

    fig.update_layout(
        height=620,
        template="simple_white",
        font=dict(size=20),
        xaxis_title="Annual house price growth (%)",
        yaxis_title="NPV difference (Buy − Rent)"
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # TAX COMPARISON
    # =====================================================
    st.subheader("Impact of tax benefits")

    b1,_ = compute_npv(house_growth, rent_growth, True)
    b0,_ = compute_npv(house_growth, rent_growth, False)

    st.metric("NPV with tax benefits", f"{b1:,.0f}")
    st.metric("NPV without tax benefits", f"{b0:,.0f}")
    st.metric("Tax benefit value", f"{b1-b0:,.0f}")

# =====================================================
# STUDENT GUIDE
# =====================================================
with tab2:

    st.header("How to interpret")

    st.markdown("""
If NPV(Buy) > NPV(Rent) → Buy  
If NPV(Rent) > NPV(Buy) → Rent  

Buying is a leveraged bet on house prices.  
Tax benefits help but rarely decide alone.
""")

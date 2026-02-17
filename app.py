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
    # BREAK-EVEN TENURE (AUTO LABEL)
    # =====================================================
    st.subheader("Break-even holding period")
    
    years = np.arange(1,31)
    tenure_diffs = []
    
    for y in years:
        old_exit = exit_year
        exit_year = y
        b,rn = compute_npv(house_growth, rent_growth, use_tax)
        tenure_diffs.append(b-rn)
        exit_year = old_exit
    
    fig_t = go.Figure()
    
    fig_t.add_scatter(
        x=years,
        y=tenure_diffs,
        mode="lines",
        line=dict(width=5, color="green"),
        name="Buy advantage"
    )
    
    fig_t.add_hline(y=0, line_width=4, line_color="black")
    
    # ---- find break-even tenure
    tenure_be = None
    for i in range(len(tenure_diffs)-1):
        if tenure_diffs[i] * tenure_diffs[i+1] < 0:
            tenure_be = years[i]
            break
    
    if tenure_be is not None:
        fig_t.add_vline(
            x=tenure_be,
            line_dash="dash",
            line_color="red",
            line_width=3
        )
    
        fig_t.add_annotation(
            x=tenure_be,
            y=max(tenure_diffs)*0.8,
            text=f"Break-even ≈ {tenure_be} yrs",
            showarrow=True,
            font=dict(size=20, color="red")
        )
    
    fig_t.update_layout(
        height=620,
        template="simple_white",
        font=dict(size=20),
        xaxis_title="Years staying in house",
        yaxis_title="NPV difference (Buy − Rent)"
    )
    
    st.plotly_chart(fig_t, use_container_width=True)
    
    if tenure_be:
        st.success(
            f"Buying becomes financially better only if you stay longer than about {tenure_be} years."
        )
    
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
    # MONTE CARLO SIMULATION
    # =====================================================
    st.subheader("Monte Carlo simulation")
    
    if st.button("Run Monte Carlo"):
    
        sims = 500
        results = []
    
        # correlation between rent & house growth
        cov = [[1,0.4],[0.4,1]]
        means = [house_growth, rent_growth]
    
        for _ in range(sims):
            hg, rg = np.random.multivariate_normal(means, cov)
            b, rn = compute_npv(hg, rg, use_tax)
            results.append(b - rn)
    
        prob = np.mean(np.array(results) > 0)
    
        st.metric("Probability buying wins", f"{prob:.2%}")
    
        fig_mc = go.Figure()
        fig_mc.add_histogram(x=results, nbinsx=40)
    
        fig_mc.update_layout(
            height=500,
            template="simple_white",
            font=dict(size=18),
            xaxis_title="NPV difference (Buy − Rent)",
            yaxis_title="Frequency"
        )
    
        st.plotly_chart(fig_mc, use_container_width=True)
    
        st.info(
            "This simulation draws random house-price and rent growth paths. "
            "The probability shown is how often buying beats renting under uncertainty."
        )

# =====================================================
# STUDENT GUIDE
# =====================================================
with tab2:

    st.header("How to interpret this simulator")

    st.markdown("""
## 🎯 Core decision rule
**If NPV(Buy) > NPV(Rent) → Buying builds more wealth**  
**If NPV(Rent) > NPV(Buy) → Renting is financially better**

This model compares *total lifetime financial impact* of buying vs renting.

It includes:
- Down payment
- EMI
- Maintenance
- Opportunity cost of capital
- House price growth
- Rent growth
- Tax benefits (India)

---

## 🧠 Big financial insight
Buying a house is essentially a:

> **leveraged investment in real estate**

You are borrowing a large amount and betting on house price growth.

If prices grow fast → buying wins  
If prices stagnate → renting wins  

---

## ⏱ Why tenure matters so much
Buying has large upfront costs:
- Stamp duty  
- Registration  
- Brokerage  
- Moving costs  

So:

**Short stay → renting better**  
**Long stay → buying better**

The break-even tenure chart shows  
how long you must stay before buying makes sense.

In India this is often:
**7–12 years**

---

## 📈 Why growth assumptions matter
Most households assume:
> “Property always goes up.”

But the simulator shows:

If growth is below break-even → renting wins  
If growth is above break-even → buying wins  

Even a 1% change in growth can flip the decision.

---

## 💸 Role of tax benefits (India)
Home-loan deductions:
- Section 24: interest deduction  
- 80C: principal deduction  

These **reduce effective EMI**.

But in most realistic cases:
> Tax benefits alone do NOT justify buying.

They only slightly shift the break-even point.

---

## 🧪 What students should experiment with
Try changing:

• Stay duration  
• Interest rate  
• Growth rate  
• Rent growth  
• Turn tax ON/OFF  
• Toggle lifetime hold  

Watch how quickly the decision flips.

---

## 🏫 Classroom discussion questions
1. Why do short-term buyers lose money?
2. What growth rate is implicit in buying?
3. Does tax policy meaningfully change decisions?
4. Is buying consumption or investment?
5. Should young professionals rent longer?

---

## 💡 Key takeaway
Most households:
- underestimate opportunity cost
- overestimate price growth
- ignore tenure risk

This simulator shows that:

> **Buying is not always financially optimal.**
""")


"""
Ипотечный калькулятор — веб-приложение на Flask.
Расчёт аннуитетного платежа и переплаты по кредиту.
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


def mortgage_calculate(principal: float, years: int, rate_percent: float) -> dict:
    """
    Аннуитетный платёж (как в банковских калькуляторах):
    Коэффициент K = (r * (1+r)^n) / ((1+r)^n - 1), платёж = P * K.
    r — месячная ставка (годовая / 12 / 100).
    Платёж округляется до копеек, итог = платёж × количество месяцев.
    """
    if principal <= 0 or years <= 0:
        return {"error": "Сумма и срок должны быть больше нуля."}
    if rate_percent < 0:
        return {"error": "Ставка не может быть отрицательной."}

    months = years * 12
    # Месячная процентная ставка (номинальная, как в РФ)
    r = (rate_percent / 100) / 12

    if r == 0:
        monthly_exact = principal / months
    else:
        # Стандартная формула аннуитета
        r_plus_one_n = (1 + r) ** months
        annuity_coef = (r * r_plus_one_n) / (r_plus_one_n - 1)
        monthly_exact = principal * annuity_coef

    # Как в банках: платёж округляется до 2 знаков
    monthly_payment = round(monthly_exact, 2)
    if r == 0:
        # При 0% общая сумма выплат = сумма кредита, переплата = 0 (без погрешности округления)
        total_paid = principal
        overpayment = 0.0
    else:
        total_paid = monthly_payment * months
        overpayment = total_paid - principal

    # График погашения: помесячно платёж, основной долг, проценты, остаток
    schedule = []
    balance = principal
    if r == 0:
        principal_per_month = round(principal / months, 2)
        for month in range(1, months + 1):
            principal_part = principal_per_month if month < months else round(balance, 2)
            payment = principal_part
            interest = 0.0
            balance = round(balance - principal_part, 2)
            schedule.append({
                "month": month,
                "payment": round(payment, 2),
                "principal": round(principal_part, 2),
                "interest": 0.0,
                "balance": max(0, balance),
            })
    else:
        for month in range(1, months + 1):
            interest = balance * r
            if month == months:
                principal_part = balance
                payment = round(principal_part + interest, 2)
            else:
                principal_part = monthly_payment - interest
                payment = monthly_payment
            balance = balance - principal_part
            schedule.append({
                "month": month,
                "payment": round(payment, 2),
                "principal": round(principal_part, 2),
                "interest": round(interest, 2),
                "balance": round(max(0, balance), 2),
            })

    return {
        "monthly_payment": monthly_payment,
        "total_paid": round(total_paid, 2),
        "overpayment": round(overpayment, 2),
        "principal": round(principal, 2),
        "months": months,
        "schedule": schedule,
    }


def mortgage_from_property_price(
    property_price: float,
    initial_payment: float,
    years: int,
    rate_percent: float,
) -> dict:
    """Сумма кредита = стоимость недвижимости − первоначальный взнос. Расчёт с учётом взноса."""
    if property_price <= 0:
        return {"error": "Стоимость недвижимости должна быть больше нуля."}
    if initial_payment < 0:
        return {"error": "Первоначальный взнос не может быть отрицательным."}
    if initial_payment >= property_price:
        return {"error": "Первоначальный взнос не может быть больше или равен стоимости недвижимости."}
    principal = property_price - initial_payment
    result = mortgage_calculate(principal, years, rate_percent)
    if "error" in result:
        return result
    result["property_price"] = round(property_price, 2)
    result["initial_payment"] = round(initial_payment, 2)
    result["total_cost"] = round(initial_payment + result["total_paid"], 2)
    result["down_payment_percent"] = round(initial_payment / property_price * 100, 1)
    result["required_monthly_income"] = round(result["monthly_payment"] / 0.4, 2)
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json() or {}
    try:
        property_price = float(data.get("property_price", 0))
        initial_payment = float(data.get("initial_payment", 0))
        years = int(data.get("years", 0))
        rate = float(data.get("rate", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Проверьте введённые данные."}), 400

    result = mortgage_from_property_price(property_price, initial_payment, years, rate)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

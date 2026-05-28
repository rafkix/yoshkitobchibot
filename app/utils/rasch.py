import math


def rasch_ability(
    correct_answers: list[float], difficulties: list[float], iterations: int = 50
) -> float:
    """
    Dichotomous Rasch modelida foydalanuvchi qobiliyatini (theta) hisoblaydi.
    correct_answers: [1.0, 0.0, 1.0, ...] — to‘g‘ri=1, noto‘g‘ri=0
    difficulties:    [0.5, -1.2, 1.3, ...] — har bir savolning b parametri
    Qaytaradi: theta (odatda -4 dan +4 gacha)
    """
    theta = 0.0

    for _ in range(iterations):
        numerator = 0.0
        denominator = 0.0

        for x, b in zip(correct_answers, difficulties):
            exp = math.exp(theta - b)
            p = exp / (1 + exp)  # P(to‘g‘ri) = e^(θ-b) / (1 + e^(θ-b))
            numerator += x - p  # residual
            denominator += p * (1 - p)  # Fisher info

        if denominator < 1e-10:
            break

        theta += numerator / denominator  # Newton-Raphson yangilanish

    return round(theta, 4)


def theta_to_score(theta: float, min_score: int = 0, max_score: int = 100) -> int:
    """
    Theta (-4..+4) ni 0-100 ballik shkala ga o‘tkazadi.
    """
    normalized = (theta + 4) / 8  # 0.0 dan 1.0 gacha
    normalized = max(0.0, min(1.0, normalized))
    return round(min_score + normalized * (max_score - min_score))

from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    today_time = datetime.today().year
    return {
        'year': today_time,
    }

from django import template

register = template.Library()


@register.filter
def duration(value):
    milliseconds = int(value or 0)
    if milliseconds < 0:
        milliseconds = 0
    minutes, _seconds = divmod(milliseconds // 1000, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"


@register.filter
def mah(value):
    return f"{float(value or 0):.1f}".replace(".", ",")


@register.filter
def bytesize(value):
    amount = float(value or 0)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if amount < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(amount)} B"
            return f"{amount:.1f} {unit}".replace(".", ",")
        amount /= 1024
    return f"{amount:.1f} GB"


@register.filter
def number(value):
    if value is None:
        return "–"
    return f"{float(value):.0f}"

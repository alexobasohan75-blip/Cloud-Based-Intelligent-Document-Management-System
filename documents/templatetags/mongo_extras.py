from django import template
register=template.Library()
@register.filter
def mongo_id(value): return str(value.get('_id')) if isinstance(value,dict) else ''
@register.filter
def dt(value):
    try: return value.strftime('%Y-%m-%d %H:%M')
    except Exception: return value

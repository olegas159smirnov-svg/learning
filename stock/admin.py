from django.contrib import admin

from stock.models import Stock

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("ticker", "name", "description")
    pass
from stock.models import Stock,Currency
@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    pass



# Register your models here.

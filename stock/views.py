from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.contrib import messages

from stock.models import Stock, AccountCurrency, AccountStock
from stock.forms import BuySellForm

# Обработчик списка акций (должен быть в файле)
def stock_list(request):
    stocks = Stock.objects.all()
    context = {
        'stocks': stocks
    }
    return render(request, 'stocks.html', context)

@login_required
def stock_detail(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    # Проверяем, есть ли у пользователя эта акция
    try:
        user_stock = AccountStock.objects.get(account=request.user.account, stock=stock)
        user_has_stock = user_stock.amount > 0
        available_amount = user_stock.amount
    except AccountStock.DoesNotExist:
        user_has_stock = False
        available_amount = 0
    
    context = {
        'stock': stock,
        'form': BuySellForm(initial={'price': stock.get_random_price()}),
        'user_has_stock': user_has_stock,
        'available_amount': available_amount
    }
    return render(request, 'stock.html', context)

@login_required
def stock_buy(request, pk):
    if request.method != "POST":
        return redirect('stock:detail', pk=pk)

    stock = get_object_or_404(Stock, pk=pk)
    form = BuySellForm(request.POST)

    if form.is_valid():
        amount = form.cleaned_data['amount']
        price = form.cleaned_data['price']
        buy_cost = price * amount

        acc_stock, created = AccountStock.objects.get_or_create(
            account=request.user.account, 
            stock=stock,
            defaults={'average_buy_cost': 0, 'amount': 0}
        )
        current_cost = acc_stock.average_buy_cost * acc_stock.amount

        total_cost = current_cost + buy_cost
        total_amount = acc_stock.amount + amount

        acc_stock.amount = total_amount
        acc_stock.average_buy_cost = total_cost / total_amount

        acc_currency, created = AccountCurrency.objects.get_or_create(
            account=request.user.account, 
            currency=stock.currency,
            defaults={'amount': 0}
        )

        if acc_currency.amount < buy_cost:
            form.add_error(None, f'На счёте недостаточно средств в валюте {stock.currency.sign}')
        else:
            acc_currency.amount = acc_currency.amount - buy_cost
            acc_stock.save()
            acc_currency.save()
            
            # Очищаем кэш портфеля
            cache.delete(f'currencies_{request.user.username}')
            cache.delete(f'stocks_{request.user.username}')
            
            messages.success(request, f'Успешно куплено {amount} акций {stock.ticker}')
            return redirect('stock:account')

    # Проверяем, есть ли у пользователя эта акция для контекста
    try:
        user_stock = AccountStock.objects.get(account=request.user.account, stock=stock)
        user_has_stock = user_stock.amount > 0
        available_amount = user_stock.amount
    except AccountStock.DoesNotExist:
        user_has_stock = False
        available_amount = 0

    context = {
        'stock': stock,
        'form': form,
        'user_has_stock': user_has_stock,
        'available_amount': available_amount
    }
    return render(request, 'stock.html', context)

@login_required
def stock_sell(request, pk):
    if request.method != "POST":
        return redirect('stock:detail', pk=pk)

    stock = get_object_or_404(Stock, pk=pk)
    form = BuySellForm(request.POST)

    if form.is_valid():
        amount = form.cleaned_data['amount']
        price = form.cleaned_data['price']
        sell_income = price * amount

        # Проверяем, есть ли у пользователя эти акции
        try:
            acc_stock = AccountStock.objects.get(
                account=request.user.account, 
                stock=stock
            )
        except AccountStock.DoesNotExist:
            form.add_error(None, f'У вас нет акций {stock.ticker}')
            
            # Контекст для рендеринга
            context = {
                'stock': stock,
                'form': form,
                'user_has_stock': False,
                'available_amount': 0
            }
            return render(request, 'stock.html', context)

        # Проверяем, достаточно ли акций для продажи
        if acc_stock.amount < amount:
            form.add_error(None, f'Недостаточно акций для продажи. У вас {acc_stock.amount} акций')
        else:
            # Уменьшаем количество акций
            acc_stock.amount -= amount
            
            # Если акций не осталось, сбрасываем среднюю цену покупки
            if acc_stock.amount == 0:
                acc_stock.average_buy_cost = 0
            
            # Пополняем валютный счет
            acc_currency, created = AccountCurrency.objects.get_or_create(
                account=request.user.account, 
                currency=stock.currency,
                defaults={'amount': 0}
            )
            
            acc_currency.amount += sell_income
            
            # Сохраняем изменения
            acc_stock.save()
            acc_currency.save()
            
            # Очищаем кэш портфеля
            cache.delete(f'currencies_{request.user.username}')
            cache.delete(f'stocks_{request.user.username}')
            
            messages.success(request, f'Успешно продано {amount} акций {stock.ticker} за {sell_income:.2f}{stock.currency.sign}')
            return redirect('stock:account')

    # Контекст для рендеринга при ошибках
    try:
        user_stock = AccountStock.objects.get(account=request.user.account, stock=stock)
        user_has_stock = user_stock.amount > 0
        available_amount = user_stock.amount
    except AccountStock.DoesNotExist:
        user_has_stock = False
        available_amount = 0

    context = {
        'stock': stock,
        'form': form,
        'user_has_stock': user_has_stock,
        'available_amount': available_amount
    }
    return render(request, 'stock.html', context)

@login_required
def account(request):
    currencies = cache.get(f'currencies_{request.user.username}')
    stocks_cache = cache.get(f'stocks_{request.user.username}')

    if currencies is None:
        currencies_data = AccountCurrency.objects.filter(
            account=request.user.account
        ).select_related('currency')
        
        currencies = [
            {
                'amount': acc_currency.amount,
                'sign': acc_currency.currency.sign
            } for acc_currency in currencies_data
        ]
        cache.set(f'currencies_{request.user.username}', currencies, 300)

    if stocks_cache is None:
        stocks_data = AccountStock.objects.filter(
            account=request.user.account,
            amount__gt=0
        ).select_related('stock')
        
        stocks_cache = [
            {
                'ticker': acc_stock.stock.ticker,
                'amount': acc_stock.amount,
                'avg': acc_stock.average_buy_cost,
                'stock_id': acc_stock.stock.id  # Добавляем ID для ссылок
            } for acc_stock in stocks_data
        ]
        cache.set(f'stocks_{request.user.username}', stocks_cache, 300)

    context = {
        'currencies': currencies,
        'stocks': stocks_cache
    }

    return render(request, template_name='account.html', context=context)
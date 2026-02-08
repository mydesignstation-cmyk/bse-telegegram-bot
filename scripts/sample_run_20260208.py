import bot, pprint, time as _time

orig = _time.strftime
_time.strftime = lambda fmt: '20260208'
try:
    print('Calling get_latest_announcement_from_api() for 20260208...')
    res = bot.get_latest_announcement_from_api()
    print('Result:')
    pprint.pprint(res)
finally:
    _time.strftime = orig

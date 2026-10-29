/* Мониторинг LAN — клиентская логика: дашборд, устройство, алерты, события,
   аналитика, настройки. Интерфейс на трёх языках: RU / ՀԱՅ / EN. */
"use strict";

const FRESH_SECONDS = 45;      // позже last_seen — считаем устройство офлайн
const POLL_MS = 5000;

/* ---------- i18n ---------- */
const I18N = {
  ru: {
    "app.name": "Мониторинг",
    "nav.dashboard": "Обзор", "nav.devices": "Компьютеры", "nav.alerts": "Оповещения",
    "nav.events": "События", "nav.analytics": "Графики", "nav.settings": "Настройки",
    "page.dashboard": "Обзор", "page.device": "Компьютер", "page.devices": "Компьютеры", "page.alerts": "Оповещения",
    "page.events": "События", "page.analytics": "Графики", "page.settings": "Настройки",
    "user.admin": "Администратор",
    "pill.ok": "сервер на связи", "pill.err": "нет связи с сервером",
    "conn.lost": "⏳ Подключение… сервер недоступен, данные не обновляются",
    "conn.restored": "✔ Связь восстановлена",
    "sub.dashboard": "Состояние сети · обновлено",
    "sub.device": "Данные сканирования ·",
    "sub.alerts": "Создаются при входе показателя во ВНИМАНИЕ или КРИТИЧНО; закрываются автоматически при восстановлении",
    "sub.events": "Подключения, офлайны, смены статусов здоровья",
    "sub.analytics": "Последние 240 отчётов агента (~20–40 минут)",
    "sub.settings": "Пороги и параметры сервера",
    "card.devices": "УСТРОЙСТВА", "card.online": "В СЕТИ", "card.alerts": "ОПОВЕЩЕНИЯ", "card.pending": "ЖДУТ РЕШЕНИЯ", "cap.alerts": "открытые оповещения", "cap.pending": "новые компьютеры — «Принять»", "cap.pendingNone": "заявок нет", "card.warning": "ВНИМАНИЕ",
    "card.critical": "КРИТИЧНО", "card.offline": "НЕ В СЕТИ",
    "cap.devices": "зарегистрировано всего", "cap.online": "отправляют данные",
    "dash.devicesSub": "все компьютеры с установленным агентом",
    "cap.warning": "показатели выше 80%", "cap.critical": "показатели выше 95%",
    "cap.offlineSome": "нет данных дольше 45 с", "cap.offlineNone": "все устройства на связи",
    "th.device": "УСТРОЙСТВО", "th.conn": "СОЕДИНЕНИЕ", "th.health": "СОСТОЯНИЕ", "th.ip": "IP", "th.name": "ИМЯ", "th.addr": "АДРЕС",
    "th.cpu": "CPU", "th.ram": "RAM", "th.disk": "ДИСК", "th.activity": "АКТИВНОСТЬ",
    "th.controls": "УПРАВЛЕНИЕ", "th.time": "ВРЕМЯ", "th.level": "УРОВЕНЬ",
    "th.message": "СООБЩЕНИЕ", "th.status": "СТАТУС", "th.event": "СОБЫТИЕ", "th.details": "ДЕТАЛИ",
    "b.online": "ОНЛАЙН", "b.offline": "ОФЛАЙН", "b.normal": "НОРМА", "b.warning": "ВНИМАНИЕ",
    "b.critical": "КРИТИЧНО", "b.open": "ОТКРЫТ", "b.resolved": "ЗАКРЫТ",
    "btn.check": "⟳ Проверить", "btn.auto": "Авто",
    "tip.check": "Обновить данные этого устройства прямо сейчас",
    "tip.auto": "Автообновление этой строки каждые 5 секунд",
    "tip.delete": "Удалить устройство и всю его историю",
    "confirm.delete": "Удалить «{name}»? Устройство и вся его история будут стёрты безвозвратно.",
    "alerts.all": "Все", "alerts.open": "Открытые", "alerts.resolved": "Закрытые",
    "alerts.empty": "Алертов пока нет — все показатели в норме. 👍",
    "alerts.emptyFilter": "В этом фильтре пусто.",
    "alerts.openCount": "Открытых: {n} · всего: {m}",
    "events.title": "Журнал событий",
    "events.empty": "Событий пока нет.",
    "event.METRIC_STATUS_CHANGED": "Смена статуса показателя",
    "event.HEALTH_CHANGED": "Смена состояния устройства",
    "event.DEVICE_OFFLINE": "Устройство отключилось",
    "event.DEVICE_ONLINE": "Устройство вышло на связь",
    "ev.health": "Состояние:", "ev.lastActivity": "Последняя активность:",
    "analytics.title": "История показателей",
    "analytics.range": "Диапазон: {from} — {to} · точек: {n}",
    "analytics.empty": "История пока пуста — агент ещё не успел отправить данные.",
    "chart.cpu": "CPU %", "chart.ram": "RAM %", "chart.disk": "Диск %",
    "settings.thresholds": "Пороги статусов",
    "settings.thresholdsSub": "при изменении статус подтверждается 3 отчётами подряд",
    "settings.system": "Система",
    "settings.systemSub": "текущие параметры сервера и агентов",
    "settings.hint": "Редактирование порогов и уведомления (email/Telegram) — на следующих уровнях развития системы.",
    "set.metric": "ПОКАЗАТЕЛЬ", "set.warnFrom": "ВНИМАНИЕ ≥", "set.critFrom": "КРИТИЧНО ≥",
    "set.cpu": "CPU", "set.ram": "RAM", "set.disk": "Диск",
    "set.temp": "Температура", "set.net": "Сеть", "set.notSet": "не нормируется",
    "set.server": "Сервер", "set.db": "База данных", "set.poll": "Интервал опроса агентов",
    "set.offlineAfter": "Считать офлайном, если молчал", "set.confirm": "Подтверждение статуса",
    "set.retention": "История метрик хранится", "set.refresh": "Обновление дашборда",
    "set.devices": "Устройств подключено", "set.address": "Адрес сервера для пользователей", "set.addressPh": "например 192.168.1.9", "set.addressAuto": "пусто — автоопределение", "set.save": "Сохранить", "set.saved": "Сохранено ✔", "set.addressBad": "Неверный адрес", "set.port": "Порт", "set.firewall": "Если пользователи не подключаются: разрешите входящий TCP-порт {port} в брандмауэре Windows (Брандмауэр → Дополнительные параметры → Правила для входящих подключений → Создать правило → Порт).", "set.noData": "нет данных",
    "state.noDevices": "Нет подключённых устройств.<br>Установи агент на компьютер — он появится здесь автоматически.",
    "state.loadError": "Не удалось загрузить данные.",
    "state.retry": "Повторить",
    "state.offline": "Нет данных для отображения.",
    "state.noHistory": "История пока пуста — агент ещё не успел отправить данные.",
    "dev.id": "ID {id} · агент {agent} · v{ver}",
    "dev.back": "← К списку",
    "dev.loadError": "Ошибка загрузки",
    "sec.cpu": "Процессор", "sec.mem": "Оперативная память", "sec.disks": "Диски",
    "sec.disksSub": "разделы и скорость ввода-вывода", "sec.net": "Сеть",
    "sec.netSub": "↓ — получение, ↑ — отправка", "sec.system": "Система",
    "sec.bios": "BIOS / материнская плата", "sec.gpu": "Видеокарта", "sec.temp": "Температура", "sec.ports": "Открытые порты", "sec.portsSub": "слушающие порты и программа", "k.proto": "Протокол", "k.port": "Порт", "k.process": "Программа", "gpu.none": "не обнаружена", "net.others": "Другие адаптеры", "net.primary": "основной",
    "k.model": "Модель", "k.manufacturer": "Производитель", "k.cores": "Физические ядра",
    "k.threads": "Логические потоки", "k.frequency": "Частота", "k.load": "Загрузка",
    "k.total": "Всего", "k.used": "Использовано", "k.free": "Свободно",
    "k.partition": "РАЗДЕЛ", "k.fs": "ФС", "k.size": "РАЗМЕР", "k.occupied": "ЗАНЯТО",
    "k.read": "Чтение", "k.write": "Запись", "k.iface": "ИНТЕРФЕЙС", "k.ipv4": "IPv4",
    "k.mac": "MAC", "k.rx": "ПОЛУЧЕНИЕ", "k.tx": "ОТПРАВКА", "k.totalIO": "ВСЕГО ↓ / ↑",
    "k.hostname": "Имя компьютера", "k.os": "Операционная система", "k.arch": "Архитектура",
    "k.uptime": "Время работы", "k.registered": "Зарегистрирован",
    "k.biosVersion": "BIOS", "k.biosVendor": "Производитель BIOS", "k.release": "Дата выпуска",
    "k.serial": "Серийный номер", "k.board": "Материнская плата", "k.boardVendor": "Производитель платы",
    "k.adapter": "Адаптер", "k.driver": "Драйвер", "k.vram": "Видеопамять",
    "k.sensors": "Датчики", "k.temp": "Температура", "k.osUnknown": "ОС неизвестна",
    "na": "нет данных", "na.sensors": "недоступны на этом устройстве",
    "hint.gpu": "Загрузка и температура — через nvidia-smi (только NVIDIA). Для других видеокарт — «нет данных».",
    "hint.tempOk": "Источники: датчики Windows (ACPI / тепловые зоны) и nvidia-smi. Значения не придумываются.",
    "hint.tempNone": "Это устройство не отдаёт температуру через Windows — «нет данных». Значения никогда не придумываются.",
    "noPartitions": "нет данных о разделах", "noIfaces": "нет данных об интерфейсах",
    "time.s": "{n} с назад", "time.m": "{n} мин назад", "time.h": "{n} ч назад",
    "time.no": "нет данных",
        "btn.addDevice": "＋ Добавить компьютер",
    "pair.title": "Добавление компьютера",
    "pair.hint": "Передайте эту строку пользователю целиком — адрес сервера уже внутри. После вашего одобрения компьютер появится в списке.",
    "pair.codeLabel": "Код сопряжения", "pair.expires": "Действует ещё",
    "pair.pending": "Ожидают одобрения",
    "pair.none": "Пока никто не подключился по этому коду.",
    "pair.approve": "Принять", "pair.reject": "Отклонить", "pair.close": "Закрыть",
    "pair.approvedMsg": "Устройство одобрено и подключается…",
    "pair.downloadHint": "Установить приложение юзера на новый компьютер — скачайте установщик:",
    "pair.copy": "Скопировать ссылку", "pair.copied": "Скопировано ✔", "pair.copyCode": "Скопировать код", "theme.title": "Тема", "theme.sea": "Морская", "theme.light": "Светлая", "theme.lavender": "Лавандовая", "theme.graphite": "Графит",
    "b.pending": "ОЖИДАЕТ",
  },
  am: {
    "app.name": "Մոնիտորինգ",
    "nav.dashboard": "Ակնարկ", "nav.devices": "Համակարգիչներ", "nav.alerts": "Ծանուցումներ",
    "nav.events": "Իրադարձություններ", "nav.analytics": "Գրաֆիկներ", "nav.settings": "Կարգավորումներ",
    "page.dashboard": "Ակնարկ", "page.device": "Համակարգիչ", "page.devices": "Համակարգիչներ", "page.alerts": "Ծանուցումներ",
    "page.events": "Իրադարձություններ", "page.analytics": "Գրաֆիկներ", "page.settings": "Կարգավորումներ",
    "user.admin": "Ադմինիստրատոր",
    "pill.ok": "սերվերը կապված է", "pill.err": "սերվերի հետ կապ չկա",
    "conn.lost": "⏳ Միանում է… սերվերը հասանելի չէ, տվյալները չեն թարմացվում",
    "conn.restored": "✔ Կապը վերականգնվեց",
    "sub.dashboard": "Ցանցի վիճակը · թարմացվել է",
    "sub.device": "Ստուգման տվյալներ ·",
    "sub.alerts": "Ստեղծվում են, երբ ցուցանիշը մտնում է ՈՒՇԱԴՐՈՒԹՅՈՒՆ կամ ԿՐԻՏԻԿ վիճակ; փակվում են ավտոմատ վերականգնման ժամանակ",
    "sub.events": "Միացումներ, անջատումներ, առողջության վիճակի փոփոխություններ",
    "sub.analytics": "Ագենտի վերջին 240 զեկույցը (~20–40 րոպե)",
    "sub.settings": "Շեմերը և սերվերի պարամետրերը",
    "card.devices": "ՍԱՐՔԵՐ", "card.online": "ԱՌՑԱՆՑ", "card.alerts": "ԾԱՆՈՒՑՈՒՄՆԵՐ", "card.pending": "ՍՊԱՍՈՒՄ ԵՆ", "cap.alerts": "բաց ծանուցումներ", "cap.pending": "նոր համակարգիչներ — «Ընդունել»", "cap.pendingNone": "հայտեր չկան", "card.warning": "ՈՒՇԱԴՐՈՒԹՅՈՒՆ",
    "card.critical": "ԿՐԻՏԻԿ", "card.offline": "ԱՆՋԱՏՎԱԾ",
    "cap.devices": "գրանցված է ընդհանուր", "cap.online": "ուղարկում են տվյալներ",
    "dash.devicesSub": "ագենտ տեղադրված բոլոր համակարգիչները",
    "cap.warning": "ցուցանիշները 80%-ից բարձր", "cap.critical": "ցուցանիշները 95%-ից բարձր",
    "cap.offlineSome": "տվյալներ չկան 45 վրկ-ից ավելի", "cap.offlineNone": "բոլոր սարքերը կապված են",
    "th.device": "ՍԱՐՔ", "th.conn": "ԿԱՊԱԿՑՈՒՄ", "th.health": "ՎԻՃԱԿ", "th.ip": "IP", "th.name": "ԱՆՈՒՆ", "th.addr": "ՀԱՍՑԵ",
    "th.cpu": "CPU", "th.ram": "RAM", "th.disk": "ՍԿԱՎԱՌԱԿ", "th.activity": "ԱԿՏԻՎՈՒԹՅՈՒՆ",
    "th.controls": "ԿԱՌԱՎԱՐՈՒՄ", "th.time": "ԺԱՄԱՆԱԿ", "th.level": "ՄԱԿԱՐԴԱԿ",
    "th.message": "ՀԱՂՈՐԴԱԳՐՈՒԹՅՈՒՆ", "th.status": "ԿԱՐԳԱՎԻՃԱԿ", "th.event": "ԻՐԱԴԱՐՁՈՒԹՅՈՒՆ", "th.details": "ՄԱՆՐԱՄԱՍՆԵՐ",
    "b.online": "ԱՌՑԱՆՑ", "b.offline": "ԱՆՋԱՏՎԱԾ", "b.normal": "ՆՈՐՄԱԼ", "b.warning": "ՈՒՇԱԴՐՈՒԹՅՈՒՆ",
    "b.critical": "ԿՐԻՏԻԿ", "b.open": "ԲԱՑ", "b.resolved": "ՓԱԿ",
    "btn.check": "⟳ Ստուգել", "btn.auto": "Ավտո",
    "tip.check": "Թարմացնել այս սարքի տվյալները հիմա",
    "tip.auto": "Այս տողի ավտոթարմացումը՝ ամեն 5 վայրկյան",
    "tip.delete": "Հեռացնել սարքը և ողջ պատմությունը",
    "confirm.delete": "Հեռացնե՞լ «{name}»-ը։ Սարքը և ողջ պատմությունը կջնջվեն անվերադարձ։",
    "alerts.all": "Բոլորը", "alerts.open": "Բաց", "alerts.resolved": "Փակ",
    "alerts.empty": "Ծանուցումներ դեռ չկան — բոլոր ցուցանիշները նորմալ են։ 👍",
    "alerts.emptyFilter": "Այս ֆիլտրում դատարկ է։",
    "alerts.openCount": "Բաց է՝ {n} · ընդհանուր՝ {m}",
    "events.title": "Իրադարձությունների մատյան",
    "events.empty": "Իրադարձություններ դեռ չկան։",
    "event.METRIC_STATUS_CHANGED": "Ցուցանիշի վիճակի փոփոխություն",
    "event.HEALTH_CHANGED": "Սարքի վիճակի փոփոխություն",
    "event.DEVICE_OFFLINE": "Սարքն անջատվեց",
    "event.DEVICE_ONLINE": "Սարքը կապվեց",
    "ev.health": "Վիճակը:", "ev.lastActivity": "Վերջին ակտիվությունը:",
    "analytics.title": "Ցուցանիշների պատմություն",
    "analytics.range": "Միջակայք՝ {from} — {to} · կետեր՝ {n}",
    "analytics.empty": "Պատմությունը դեռ դատարկ է — ագենտը տվյալներ չի հասցրել ուղարկել։",
    "chart.cpu": "CPU %", "chart.ram": "RAM %", "chart.disk": "Սկավառակ %",
    "settings.thresholds": "Կարգավիճակների շեմեր",
    "settings.thresholdsSub": "փոփոխության դեպքում վիճակը հաստատվում է 3 զեկույցով անընդմեջ",
    "settings.system": "Համակարգ",
    "settings.systemSub": "սերվերի և ագենտների ընթացիկ պարամետրերը",
    "settings.hint": "Շեմերի խմբագրումը և ծանուցումները (email/Telegram) — համակարգի զարգացման հաջորդ փուլերում։",
    "set.metric": "ՑՈՒՑԱՆԻՇ", "set.warnFrom": "ՈՒՇԱԴՐՈՒԹՅՈՒՆ ≥", "set.critFrom": "ԿՐԻՏԻԿ ≥",
    "set.cpu": "CPU", "set.ram": "RAM", "set.disk": "Սկավառակ",
    "set.temp": "Ջերմաստիճան", "set.net": "Ցանց", "set.notSet": "չի կարգավորվում",
    "set.server": "Սերվեր", "set.db": "Տվյալների բազա", "set.poll": "Ագենտների հարցման ինտերվալը",
    "set.offlineAfter": "Անջատված համարել, եթե լռել է", "set.confirm": "Վիճակի հաստատում",
    "set.retention": "Մետրիկաների պատմությունը պահվում է", "set.refresh": "Դաշբորդի թարմացումը",
    "set.devices": "Միացված սարքեր", "set.address": "Սերվերի հասցեն օգտատերերի համար", "set.addressPh": "օրինակ 192.168.1.9", "set.addressAuto": "դատարկ — ավտոմատ որոշում", "set.save": "Պահպանել", "set.saved": "Պահպանված է ✔", "set.addressBad": "Սխալ հասցե", "set.port": "Պորտ", "set.firewall": "Եթե օգտատերերը չեն միանում՝ թույլատրեք մուտքային TCP պորտ {port}-ը Windows-ի firewall-ում։", "set.noData": "տվյալներ չկան",
    "state.noDevices": "Միացված սարքեր չկան։<br>Տեղադրիր ագենտը համակարգչի վրա — այն ինքնուրույն կհայտնվի այստեղ։",
    "state.loadError": "Չհաջողվեց բեռնել տվյալները։",
    "state.retry": "Կրկնել",
    "state.offline": "Ցուցադրելու տվյալներ չկան։",
    "state.noHistory": "Պատմությունը դեռ դատարկ է — ագենտը տվյալներ չի հասցրել ուղարկել։",
    "dev.id": "ID {id} · ագենտ {agent} · v{ver}",
    "dev.back": "← Ցանկին",
    "dev.loadError": "Բեռնման սխալ",
    "sec.cpu": "Պրոցեսոր", "sec.mem": "Օպերատիվ հիշողություն", "sec.disks": "Սկավառակներ",
    "sec.disksSub": "բաժանումներ և մուտք/ելքի արագություն", "sec.net": "Ցանց",
    "sec.netSub": "↓ — ընդունում, ↑ — ուղարկում", "sec.system": "Համակարգ",
    "sec.bios": "BIOS / մայր պլատա", "sec.gpu": "Վիդեոքարտ", "sec.temp": "Ջերմաստիճան", "sec.ports": "Բաց պորտեր", "sec.portsSub": "լսող պորտեր և ծրագիր", "k.proto": "Արձանագրություն", "k.port": "Պորտ", "k.process": "Ծրագիր", "gpu.none": "չի հայտնաբերվել", "net.others": "Այլ ադապտերներ", "net.primary": "հիմնական",
    "k.model": "Մոդել", "k.manufacturer": "Արտադրող", "k.cores": "Ֆիզիկական միջուկներ",
    "k.threads": "Տրամաբանական հոսքեր", "k.frequency": "Հաճախականություն", "k.load": "Բեռնվածություն",
    "k.total": "Ընդհանուր", "k.used": "Օգտագործված", "k.free": "Ազատ",
    "k.partition": "ԲԱԺԱՆՈՒՄ", "k.fs": "ՖՍ", "k.size": "ՉԱՓՍ", "k.occupied": "ԶԲԱՂՎԱԾ",
    "k.read": "Ընթերցում", "k.write": "Գրառում", "k.iface": "ԻՆՏԵՐՖԵՅՍ", "k.ipv4": "IPv4",
    "k.mac": "MAC", "k.rx": "ԸՆԴՈՒՆՈՒՄ", "k.tx": "ՈՒՂԱՐԿՈՒՄ", "k.totalIO": "ԸՆԴՀԱՆՈՒՐ ↓ / ↑",
    "k.hostname": "Համակարգչի անունը", "k.os": "Օպերացիոն համակարգ", "k.arch": "Ճարտարապետություն",
    "k.uptime": "Աշխատանքի ժամանակը", "k.registered": "Գրանցված է",
    "k.biosVersion": "BIOS", "k.biosVendor": "BIOS-ի արտադրողը", "k.release": "Թողարկման ամսաթիվ",
    "k.serial": "Սերիական համար", "k.board": "Մայր պլատա", "k.boardVendor": "Պլատայի արտադրողը",
    "k.adapter": "Ադապտեր", "k.driver": "Դրայվեր", "k.vram": "Վիդեոհիշողություն",
    "k.sensors": "Սենսորներ", "k.temp": "Ջերմաստիճան", "k.osUnknown": "ՕՀ-ը անհայտ է",
    "na": "տվյալներ չկան", "na.sensors": "անհասանելի են այս սարքի վրա",
    "hint.gpu": "Բեռնվածությունը և ջերմաստիճանը՝ nvidia-smi-ի միջոցով (միայն NVIDIA)։ Այլ վիդեոքարտերի համար՝ «տվյալներ չկան»։",
    "hint.tempOk": "Աղբյուրներ՝ Windows-ի սենսորներ (ACPI / ջերմային գոտիներ) և nvidia-smi։ Արժեքները չեն հորինվում։",
    "hint.tempNone": "Այս սարքը Windows-ի միջոցով ջերմաստիճան չի տալիս — «տվյալներ չկան»։ Արժեքները երբեք չեն հորինվում։",
    "noPartitions": "բաժանումների մասին տվյալներ չկան", "noIfaces": "ինտերֆեյսների մասին տվյալներ չկան",
    "time.s": "{n} վրկ առաջ", "time.m": "{n} րոպե առաջ", "time.h": "{n} ժ առաջ",
    "time.no": "տվյալներ չկան",
        "btn.addDevice": "＋ Ավելացնել համակարգիչ",
    "pair.title": "Համակարգչի ավելացում",
    "pair.hint": "Փոխանցեք այս տողը օգտատիրոջն ամբողջությամբ — սերվերի հասցեն արդեն ներսում է։ Ձեր հաստատումից հետո համակարգիչը կհայտնվի ցուցակում։",
    "pair.codeLabel": "Զուգակցման կոդը", "pair.expires": "Գործում է ևս",
    "pair.pending": "Սպասում են հաստատման",
    "pair.none": "Այս կոդով ոչ ոք դեռ չի միացել։",
    "pair.approve": "Ընդունել", "pair.reject": "Մերժել", "pair.close": "Փակել",
    "pair.approvedMsg": "Սարքը հաստատվեց և միանում է…",
    "pair.downloadHint": "Նոր համակարգչում տեղադրելու համար ներբեռնեք տեղակայիչը՝",
    "pair.copy": "Պատճենել հղումը", "pair.copied": "Պատճենված է ✔", "pair.copyCode": "Պատճենել կոդը", "theme.title": "Թեմա", "theme.sea": "Ծովային", "theme.light": "Լուսավոր", "theme.lavender": "Լավանդա", "theme.graphite": "Գրաֆիտ",
    "b.pending": "ՍՊԱՍՈՒՄ",
  },
  en: {
    "app.name": "Monitoring",
    "nav.dashboard": "Overview", "nav.devices": "Computers", "nav.alerts": "Alerts",
    "nav.events": "Events", "nav.analytics": "Charts", "nav.settings": "Settings",
    "page.dashboard": "Overview", "page.device": "Computer", "page.devices": "Computers", "page.alerts": "Alerts",
    "page.events": "Events", "page.analytics": "Charts", "page.settings": "Settings",
    "user.admin": "Administrator",
    "pill.ok": "server connected", "pill.err": "no server connection",
    "conn.lost": "⏳ Connecting… server unreachable, data is not refreshed",
    "conn.restored": "✔ Connection restored",
    "sub.dashboard": "Network status · updated",
    "sub.device": "Scan data ·",
    "sub.alerts": "Created when a metric enters WARNING or CRITICAL; closed automatically on recovery",
    "sub.events": "Connections, outages, health status changes",
    "sub.analytics": "Last 240 agent reports (~20–40 minutes)",
    "sub.settings": "Thresholds and server parameters",
    "card.devices": "DEVICES", "card.online": "ONLINE", "card.alerts": "ALERTS", "card.pending": "AWAITING DECISION", "cap.alerts": "open alerts", "cap.pending": "new computers — click Approve", "cap.pendingNone": "no requests", "card.warning": "WARNING",
    "card.critical": "CRITICAL", "card.offline": "OFFLINE",
    "cap.devices": "registered in total", "cap.online": "reporting data",
    "dash.devicesSub": "all computers with the agent installed",
    "cap.warning": "metrics above 80%", "cap.critical": "metrics above 95%",
    "cap.offlineSome": "no data for over 45 s", "cap.offlineNone": "all devices connected",
    "th.device": "DEVICE", "th.conn": "CONNECTION", "th.health": "STATE", "th.ip": "IP", "th.name": "NAME", "th.addr": "ADDRESS",
    "th.cpu": "CPU", "th.ram": "RAM", "th.disk": "DISK", "th.activity": "ACTIVITY",
    "th.controls": "CONTROLS", "th.time": "TIME", "th.level": "LEVEL",
    "th.message": "MESSAGE", "th.status": "STATUS", "th.event": "EVENT", "th.details": "DETAILS",
    "b.online": "ONLINE", "b.offline": "OFFLINE", "b.normal": "NORMAL", "b.warning": "WARNING",
    "b.critical": "CRITICAL", "b.open": "OPEN", "b.resolved": "RESOLVED",
    "btn.check": "⟳ Check", "btn.auto": "Auto",
    "tip.check": "Refresh this device's data right now",
    "tip.auto": "Auto-refresh this row every 5 seconds",
    "tip.delete": "Delete the device and its entire history",
    "confirm.delete": "Delete \"{name}\"? The device and all of its history will be removed permanently.",
    "alerts.all": "All", "alerts.open": "Open", "alerts.resolved": "Resolved",
    "alerts.empty": "No alerts yet — all metrics are in norm. 👍",
    "alerts.emptyFilter": "Nothing in this filter.",
    "alerts.openCount": "Open: {n} · total: {m}",
    "events.title": "Event log",
    "events.empty": "No events yet.",
    "event.METRIC_STATUS_CHANGED": "Metric status changed",
    "event.HEALTH_CHANGED": "Device health changed",
    "event.DEVICE_OFFLINE": "Device went offline",
    "event.DEVICE_ONLINE": "Device came online",
    "ev.health": "Health:", "ev.lastActivity": "Last activity:",
    "analytics.title": "Metric history",
    "analytics.range": "Range: {from} — {to} · points: {n}",
    "analytics.empty": "History is empty — the agent has not reported yet.",
    "chart.cpu": "CPU %", "chart.ram": "RAM %", "chart.disk": "Disk %",
    "settings.thresholds": "Status thresholds",
    "settings.thresholdsSub": "after a change the status is confirmed by 3 consecutive reports",
    "settings.system": "System",
    "settings.systemSub": "current server and agent parameters",
    "settings.hint": "Threshold editing and notifications (email/Telegram) are planned in later stages.",
    "set.metric": "METRIC", "set.warnFrom": "WARNING ≥", "set.critFrom": "CRITICAL ≥",
    "set.cpu": "CPU", "set.ram": "RAM", "set.disk": "Disk",
    "set.temp": "Temperature", "set.net": "Network", "set.notSet": "not evaluated",
    "set.server": "Server", "set.db": "Database", "set.poll": "Agent polling interval",
    "set.offlineAfter": "Consider offline after silence of", "set.confirm": "Status confirmation",
    "set.retention": "Metric history is kept for", "set.refresh": "Dashboard refresh",
    "set.devices": "Connected devices", "set.address": "Server address for users", "set.addressPh": "e.g. 192.168.1.9", "set.addressAuto": "empty — auto-detect", "set.save": "Save", "set.saved": "Saved ✔", "set.addressBad": "Invalid address", "set.port": "Port", "set.firewall": "If users cannot connect: allow inbound TCP port {port} in Windows Firewall (Advanced settings → Inbound Rules → New Rule → Port).", "set.noData": "no data",
    "state.noDevices": "No devices connected.<br>Install the agent on a computer — it will appear here automatically.",
    "state.loadError": "Failed to load data.",
    "state.retry": "Retry",
    "state.offline": "No data to display.",
    "state.noHistory": "History is empty — the agent has not reported yet.",
    "dev.id": "ID {id} · agent {agent} · v{ver}",
    "dev.back": "← Back to list",
    "dev.loadError": "Loading error",
    "sec.cpu": "Processor", "sec.mem": "Memory", "sec.disks": "Disks",
    "sec.disksSub": "partitions and I/O speeds", "sec.net": "Network",
    "sec.netSub": "↓ — received, ↑ — sent", "sec.system": "System",
    "sec.bios": "BIOS / motherboard", "sec.gpu": "GPU", "sec.temp": "Temperature", "sec.ports": "Open ports", "sec.portsSub": "listening ports and program", "k.proto": "Protocol", "k.port": "Port", "k.process": "Program", "gpu.none": "not detected", "net.others": "Other adapters", "net.primary": "primary",
    "k.model": "Model", "k.manufacturer": "Manufacturer", "k.cores": "Physical cores",
    "k.threads": "Logical threads", "k.frequency": "Frequency", "k.load": "Load",
    "k.total": "Total", "k.used": "Used", "k.free": "Free",
    "k.partition": "PARTITION", "k.fs": "FS", "k.size": "SIZE", "k.occupied": "USED",
    "k.read": "Read", "k.write": "Write", "k.iface": "INTERFACE", "k.ipv4": "IPv4",
    "k.mac": "MAC", "k.rx": "RECEIVED", "k.tx": "SENT", "k.totalIO": "TOTAL ↓ / ↑",
    "k.hostname": "Computer name", "k.os": "Operating system", "k.arch": "Architecture",
    "k.uptime": "Uptime", "k.registered": "Registered",
    "k.biosVersion": "BIOS", "k.biosVendor": "BIOS vendor", "k.release": "Release date",
    "k.serial": "Serial number", "k.board": "Motherboard", "k.boardVendor": "Board vendor",
    "k.adapter": "Adapter", "k.driver": "Driver", "k.vram": "Video memory",
    "k.sensors": "Sensors", "k.temp": "Temperature", "k.osUnknown": "OS unknown",
    "na": "no data", "na.sensors": "unavailable on this device",
    "hint.gpu": "Load and temperature come from nvidia-smi (NVIDIA only). Other GPUs show “no data”.",
    "hint.tempOk": "Sources: Windows sensors (ACPI / thermal zones) and nvidia-smi. Values are never invented.",
    "hint.tempNone": "This device does not expose temperature through Windows — “no data”. Values are never invented.",
    "noPartitions": "no partition data", "noIfaces": "no interface data",
    "time.s": "{n} s ago", "time.m": "{n} min ago", "time.h": "{n} h ago",
    "time.no": "no data",
        "btn.addDevice": "＋ Add computer",
    "pair.title": "Add a computer",
    "pair.hint": "Give this whole line to the user — the server address is already inside. The computer appears in the list once you approve it.",
    "pair.codeLabel": "Pairing code", "pair.expires": "Valid for",
    "pair.pending": "Awaiting approval",
    "pair.none": "Nobody has used this code yet.",
    "pair.approve": "Approve", "pair.reject": "Reject", "pair.close": "Close",
    "pair.approvedMsg": "Device approved and connecting…",
    "pair.downloadHint": "To install the user app on a new computer, download the installer:",
    "pair.copy": "Copy link", "pair.copied": "Copied ✔", "pair.copyCode": "Copy code", "theme.title": "Theme", "theme.sea": "Sea", "theme.light": "Light", "theme.lavender": "Lavender", "theme.graphite": "Graphite",
    "b.pending": "PENDING",
  },
};

let lang = document.documentElement.dataset.lang || localStorage.getItem("monitoring_lang") || "ru";
const LOCALES = { ru: "ru-RU", am: "hy-AM", en: "en-US" };

function t(key, params) {
  let text = I18N[lang]?.[key] ?? I18N.ru[key] ?? key;
  if (params) for (const [name, value] of Object.entries(params)) {
    text = text.replace(`{${name}}`, value);
  }
  return text;
}

function applyI18n() {
  localStorage.setItem("monitoring_lang", lang);
  document.documentElement.lang = lang;
  const pageKey = document.body.dataset.page || "dashboard";
  document.title = `${t("page." + pageKey)} · ${t("app.name")}`;
  const titleEl = document.getElementById("page-title");
  if (titleEl) titleEl.textContent = t("page." + pageKey);
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  markTheme();
  document.querySelectorAll(".lang-switch button[data-lang]").forEach((b) =>
    b.classList.toggle("active", b.dataset.lang === lang)
  );
}

document.addEventListener("click", (event) => {
  const langButton = event.target.closest(".lang-switch button[data-lang]");
  if (!langButton || langButton.dataset.lang === lang) return;
  lang = langButton.dataset.lang;
  applyI18n();
  saveUiPrefs();
  const renderer = PAGE_RENDERERS[document.body.dataset.page];
  if (renderer) renderer();
});

/* ---------- темы оформления ---------- */
function saveUiPrefs() {
  // Окно приложения не хранит localStorage между запусками — выбор хранится на сервере.
  // Тема и язык уходят вместе, чтобы два запроса подряд не затирали друг друга.
  const prefs = { theme: document.documentElement.dataset.theme || "sea", lang };
  fetch("/api/monitoring/ui-prefs", {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(prefs),
  }).catch(() => {});
}

function markTheme() {
  const current = document.documentElement.dataset.theme || "sea";
  document.querySelectorAll("[data-theme-choice]").forEach((b) =>
    b.classList.toggle("active", b.dataset.themeChoice === current)
  );
}

document.addEventListener("click", (event) => {
  const pop = document.getElementById("theme-pop");
  if (event.target.closest("#theme-btn")) {
    if (pop) pop.hidden = !pop.hidden;
    return;
  }
  const choice = event.target.closest("[data-theme-choice]");
  if (choice) {
    document.documentElement.dataset.theme = choice.dataset.themeChoice;
    markTheme();
    saveUiPrefs();
  }
  if (pop && !event.target.closest("#theme-pop")) pop.hidden = true;
});

/* ---------- утилиты ---------- */
const $ = (sel) => document.querySelector(sel);

async function fetchJson(url, options) {
  const response = await fetch(url, { cache: "no-store", ...options });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("login required");
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

function fmtBytes(value) {
  if (value === null || value === undefined) return null;
  const units = lang === "en" ? ["B", "KB", "MB", "GB", "TB"]
    : lang === "am" ? ["Բ", "ԿԲ", "ՄԲ", "ԳԲ", "ՏԲ"]
    : ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  let size = Number(value), i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function fmtSpeed(value) {
  if (value === null || value === undefined) return null;
  const perSecond = lang === "en" ? "/s" : lang === "am" ? "/վրկ" : "/с";
  return `${fmtBytes(value)}${perSecond}`;
}

function fmtUptime(seconds) {
  if (seconds === null || seconds === undefined) return null;
  let rest = Math.floor(Number(seconds));
  const days = Math.floor(rest / 86400); rest %= 86400;
  const hours = Math.floor(rest / 3600); rest %= 3600;
  const minutes = Math.floor(rest / 60);
  if (lang === "en") {
    if (days > 0) return `${days} d ${hours} h`;
    if (hours > 0) return `${hours} h ${minutes} min`;
    return `${minutes} min`;
  }
  if (lang === "am") {
    if (days > 0) return `${days} օր ${hours} ժ`;
    if (hours > 0) return `${hours} ժ ${minutes} ր`;
    return `${minutes} ր`;
  }
  if (days > 0) return `${days} д. ${hours} ч.`;
  if (hours > 0) return `${hours} ч. ${minutes} мин.`;
  return `${minutes} мин.`;
}

function parseDate(iso) {
  if (!iso) return null;
  // Страховка: наивное время считаем UTC (так его хранит сервер).
  const normalized = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function fmtTime(iso) {
  const date = parseDate(iso);
  return date ? date.toLocaleString(LOCALES[lang], { hour12: false }) : "—";
}

function agoText(iso) {
  const date = parseDate(iso);
  if (!date) return t("time.no");
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (!Number.isFinite(seconds)) return t("time.no");
  if (seconds < 60) return t("time.s", { n: seconds });
  if (seconds < 3600) return t("time.m", { n: Math.floor(seconds / 60) });
  return t("time.h", { n: Math.floor(seconds / 3600) });
}

function isFresh(device) {
  const date = parseDate(device.last_seen);
  if (!date) return false;
  const seconds = (Date.now() - date.getTime()) / 1000;
  return Number.isFinite(seconds) && seconds <= FRESH_SECONDS;
}

function percentBar(value) {
  if (value === null || value === undefined) return `<span class="na mono">—</span>`;
  const tone = value >= 95 ? "crit" : value >= 80 ? "warn" : "";
  return `<span class="bar"><span class="track"><span class="fill ${tone}" style="width:${Math.min(value, 100)}%"></span></span><span class="num">${Math.round(value)}%</span></span>`;
}

function badge(kind, text, title = "") {
  return `<span class="badge b-${kind}" ${title ? `title="${esc(title)}"` : ""}><i></i>${esc(text)}</span>`;
}

function connBadge(device) {
  if (device.connection_status === "PENDING_APPROVAL") return badge("warn", t("b.pending"));
  return isFresh(device)
    ? badge("ok", t("b.online"), `${t("ev.lastActivity")} ${agoText(device.last_seen)}`)
    : badge("off", t("b.offline"), `${t("ev.lastActivity")} ${agoText(device.last_seen)}`);
}

function healthBadge(status) {
  if (status === "NORMAL") return badge("ok", t("b.normal"));
  if (status === "WARNING") return badge("warn", t("b.warning"));
  if (status === "CRITICAL") return badge("crit", t("b.critical"));
  return `<span class="badge b-off"><i></i>—</span>`;
}

function monitorIcon() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>`;
}

let connectionWasLost = false;

function setServerPill(ok) {
  const pill = $("#server-pill");
  if (!pill) return;
  pill.classList.toggle("ok", ok);
  pill.classList.toggle("err", !ok);
  pill.lastChild.textContent = ok ? t("pill.ok") : t("pill.err");
  const banner = document.getElementById("conn-banner");
  if (banner) {
    if (!ok) {
      banner.textContent = t("conn.lost");
      banner.className = "conn-banner err";
      banner.style.display = "block";
      connectionWasLost = true;
    } else if (connectionWasLost) {
      banner.textContent = t("conn.restored");
      banner.className = "conn-banner ok";
      banner.style.display = "block";
      connectionWasLost = false;
      setTimeout(function () { banner.style.display = "none"; }, 3000);
    } else {
      banner.style.display = "none";
    }
  }
}

function schedule(fn) {
  const tick = async () => { if (!document.hidden) await fn(); };
  tick();
  setInterval(tick, POLL_MS);
}

// Level 7: баннер состояния связи (вставляется в шапку на всех страницах)
function ensureConnBanner() {
  if (document.getElementById("conn-banner")) return;
  const banner = document.createElement("div");
  banner.id = "conn-banner";
  banner.className = "conn-banner";
  banner.style.display = "none";
  const topbar = document.querySelector(".topbar") || document.body;
  topbar.parentNode.insertBefore(banner, topbar.nextSibling);
}

/* ---------- дашборд и страница устройств ---------- */
async function renderDashboard() {
  let devices;
  try {
    devices = await fetchJson("/api/devices");
    setServerPill(true);
  } catch {
    setServerPill(false);
    renderDevicesError();
    return;
  }
  const subtitle = $("#page-subtitle");
  if (subtitle) subtitle.textContent = `${t("sub.dashboard")} ${new Date().toLocaleTimeString(LOCALES[lang], { hour12: false })}`;

  const online = devices.filter(isFresh);
  const offline = devices.length - online.length;
  const warning = devices.filter((d) => d.health_status === "WARNING").length;
  const critical = devices.filter((d) => d.health_status === "CRITICAL").length;
  const pending = devices.filter((d) => d.connection_status === "PENDING_APPROVAL").length;
  let openAlerts = null;
  try {
    openAlerts = (await fetchJson("/api/monitoring/alerts?limit=1000")).filter((a) => a.status === "OPEN").length;
  } catch { /* нет данных — показываем «—» */ }
  $("#stat-cards").innerHTML = `
    <div class="stat ok"><div class="label">${t("card.online")}</div><div class="value">${online.length}</div><div class="cap">${t("cap.online")}</div></div>
    <div class="stat ${offline ? "off" : ""}"><div class="label">${t("card.offline")}</div><div class="value">${offline}</div><div class="cap">${offline ? t("cap.offlineSome") : t("cap.offlineNone")}</div></div>
    <div class="stat ${critical ? "crit" : openAlerts || warning ? "warn" : ""}"><div class="label">${t("card.alerts")}</div><div class="value">${openAlerts ?? "—"}</div><div class="cap">${critical ? `⚠ ${t("card.critical")}: ${critical}` : t("cap.alerts")}</div></div>
    <div class="stat ${pending ? "accent" : ""}"><div class="label">${t("card.pending")}</div><div class="value">${pending}</div><div class="cap">${pending ? t("cap.pending") : t("cap.pendingNone")}</div></div>`;

  renderDeviceTable(devices);
  if (pairingModalOpen) updatePairingModal();
}

/* Страница «Устройства» — та же таблица, но без сводных карточек. */
async function renderDevices() {
  let devices;
  try {
    devices = await fetchJson("/api/devices");
    setServerPill(true);
  } catch {
    setServerPill(false);
    renderDevicesError();
    return;
  }
  const subtitle = $("#page-subtitle");
  if (subtitle) subtitle.textContent = t("sub.dashboard").split(" ·")[0] + ` · ${devices.length} ${lang === "en" ? "device(s)" : lang === "am" ? "սարք" : "шт."}`;
  renderDeviceTable(devices);
}

/* Общая таблица устройств для дашборда и страницы «Устройства». */
function renderDeviceTable(devices) {
  const box = $("#devices-table-box");
  if (!box) return;
  if (!devices.length) {
    box.innerHTML = `<div class="state-box">${t("state.noDevices")}</div>`;
    return;
  }
  const autoOff = autoOffSet();
  const rows = devices.map((device) => {
    const latest = device.latest || {};
    const autoOn = !autoOff.has(device.id);
    return `<tr class="${isFresh(device) ? "" : "is-off"} ${autoOn ? "" : "is-paused"} row-link" data-href="/devices/${device.id}">
      ${buildDeviceRow(device, latest)}
      <td class="controls">
        <button class="mini-btn" data-refresh="${device.id}" title="${esc(t("tip.check"))}">${esc(t("btn.check"))}</button>
        <button class="mini-btn auto ${autoOn ? "on" : ""}" data-auto="${device.id}" title="${esc(t("tip.auto"))}">${esc(t("btn.auto"))}</button>
        <button class="mini-btn danger" data-delete="${device.id}" data-name="${esc(device.hostname)}" title="${esc(t("tip.delete"))}">✕</button>
      </td>
    </tr>`;
  }).join("");
  box.innerHTML = `<table>
    <thead><tr><th>${t("th.name")}</th><th>${t("th.addr")}</th><th>${t("th.health")}</th><th>${t("th.cpu")}</th><th>${t("th.ram")}</th><th>${t("th.disk")}</th><th>${t("th.controls")}</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function buildDeviceRow(device, latest) {
  return `
      <td><a class="dev-name" href="/devices/${device.id}"><span class="dev-ico">${monitorIcon()}</span>${esc(device.hostname)}</a>
        <div class="dev-ago mono" title="${esc(fmtTime(device.last_seen))}">${esc(agoText(device.last_seen))}</div></td>
      <td class="mono" style="color:var(--muted)">${esc(device.ip_address ?? "—")}</td>
      <td><div class="state-cell">${connBadge(device)}${healthBadge(device.health_status)}</div></td>
      <td>${percentBar(latest.cpu_percent)}</td>
      <td>${percentBar(latest.ram_percent)}</td>
      <td>${percentBar(latest.disk_percent)}</td>`;
}

function renderDevicesError() {
  const box = $("#devices-table-box");
  if (box) box.innerHTML = `<div class="state-box">${t("state.loadError")}<button class="btn" onclick="renderDashboard()">${t("state.retry")}</button></div>`;
}

/* ---------- управление строкой: Проверить / Авто / Удалить ---------- */
const AUTO_OFF_KEY = "monitoring_auto_off";

function autoOffSet() {
  try {
    return new Set(JSON.parse(localStorage.getItem(AUTO_OFF_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveAutoOff(set) {
  localStorage.setItem(AUTO_OFF_KEY, JSON.stringify([...set]));
}

function toggleDeviceAuto(button) {
  const id = Number(button.dataset.auto);
  const off = autoOffSet();
  if (off.has(id)) off.delete(id);
  else off.add(id);
  saveAutoOff(off);
  button.classList.toggle("on", !off.has(id));
  const row = button.closest("tr");
  if (row) row.classList.toggle("is-paused", off.has(id));
}

async function refreshDeviceRow(button) {
  const id = Number(button.dataset.refresh);
  button.classList.add("spinning");
  button.disabled = true;
  try {
    const device = await fetchJson(`/api/devices/${id}`);
    const row = button.closest("tr");
    if (row) {
      row.innerHTML = buildDeviceRow(device, device.latest || {});
    }
  } catch {
    setServerPill(false);
  } finally {
    const again = document.querySelector(`button[data-refresh="${id}"]`);
    if (again) {
      again.classList.remove("spinning");
      again.disabled = false;
    }
  }
}

async function deleteDevice(button) {
  const id = Number(button.dataset.delete);
  const name = button.dataset.name || `ID ${id}`;
  // Опасное действие — подтверждение обязательно (план проекта, раздел 25).
  if (!window.confirm(t("confirm.delete", { name }))) return;
  button.disabled = true;
  try {
    const response = await fetch(`/api/devices/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const off = autoOffSet();
    off.delete(id);
    saveAutoOff(off);
    await renderDashboard();
  } catch {
    setServerPill(false);
    button.disabled = false;
  }
}

/* ---------- страница устройства ---------- */
function kv(key, value, unit = "") {
  const text = value === null || value === undefined || value === "" ? t("na") : `${value}${unit}`;
  const na = text === t("na") ? " na" : "";
  return `<div class="kv"><span class="k">${esc(key)}</span><span class="v${na}">${esc(text)}</span></div>`;
}

function renderDevice(device, snapshot) {
  $("#dev-hostname").textContent = device.hostname;
  $("#dev-ico").innerHTML = monitorIcon();
  $("#dev-meta").textContent = t("dev.id", { id: device.id, agent: device.agent_id, ver: device.agent_version });
  $("#dev-badges").innerHTML = connBadge(device) + badge("neutral", esc(device.os_name || t("k.osUnknown")));
  $("#page-subtitle").textContent = `${t("sub.device")} ${agoText(device.last_seen)}`;

  const p = snapshot || {};
  const cpu = p.cpu || {}, ram = p.ram || {}, disk = p.disk || {}, net = p.network || {};
  const system = p.system || {}, bios = p.bios || {}, gpu = p.gpu || {};
  const io = disk.io || {}, temp = p.temperature || {};

  const partitions = (disk.partitions || []).map((part) => `<tr>
      <td class="mono">${esc(part.mountpoint ?? part.device ?? "—")}</td>
      <td class="mono" style="color:var(--muted)">${esc(part.filesystem ?? "—")}</td>
      <td class="mono">${esc(fmtBytes(part.total_bytes) ?? "—")}</td>
      <td class="mono">${esc(fmtBytes(part.used_bytes) ?? "—")}</td>
      <td>${percentBar(part.usage_percent)}</td>
    </tr>`).join("") || `<tr><td colspan="5" style="text-align:center;color:var(--muted)">${t("noPartitions")}</td></tr>`;

  const ifaceRow = (iface) => `<tr>
      <td>${esc(iface.name)}${iface.primary ? ` <span class="badge-mini">${t("net.primary")}</span>` : ""}</td>
      <td class="mono" style="color:var(--muted)">${esc((iface.ipv4 || []).join(", ") || "—")}</td>
      <td class="mono" style="color:var(--muted)">${esc(iface.mac || "—")}</td>
      <td class="mono">↓ ${esc(fmtSpeed(iface.rx_speed_Bps) ?? "—")}</td>
      <td class="mono">↑ ${esc(fmtSpeed(iface.tx_speed_Bps) ?? "—")}</td>
      <td class="mono">${esc(fmtBytes(iface.rx_bytes) ?? "—")} / ${esc(fmtBytes(iface.tx_bytes) ?? "—")}</td>
    </tr>`;
  // Основной активный адаптер — в таблице, остальные (виртуальные и т.п.) свёрнуты.
  const allIfaces = net.interfaces || [];
  const mainIfaces = allIfaces.some((i) => i.primary) ? allIfaces.filter((i) => i.primary) : allIfaces;
  const otherIfaces = allIfaces.filter((i) => !mainIfaces.includes(i));
  const interfaces = mainIfaces.map(ifaceRow).join("") || `<tr><td colspan="6" style="text-align:center;color:var(--muted)">${t("noIfaces")}</td></tr>`;
  const ifaceHead = `<thead><tr><th>${t("k.iface")}</th><th>${t("k.ipv4")}</th><th>${t("k.mac")}</th><th>${t("k.rx")}</th><th>${t("k.tx")}</th><th>${t("k.totalIO")}</th></tr></thead>`;
  const otherBlock = otherIfaces.length
    ? `<details class="more"><summary>${t("net.others")} (${otherIfaces.length})</summary><table>${ifaceHead}<tbody>${otherIfaces.map(ifaceRow).join("")}</tbody></table></details>`
    : "";

  const portsList = (p.ports || {}).listening;
  const portsBlock = Array.isArray(portsList)
    ? (portsList.length
      ? `<div class="scroll-box"><table><thead><tr><th>${t("k.proto")}</th><th>${t("k.port")}</th><th>${t("k.ipv4")}</th><th>${t("k.process")}</th></tr></thead><tbody>${portsList.map((port) => `<tr>
          <td class="mono">${esc(port.protocol)}</td><td class="mono">${esc(port.port)}</td>
          <td class="mono" style="color:var(--muted)">${esc(port.address)}</td><td>${esc(port.process ?? t("na"))}</td></tr>`).join("")}</tbody></table></div>`
      : `<div class="kv"><span class="k">${t("sec.ports")}</span><span class="v">0</span></div>`)
    : `<div class="kv"><span class="k">${t("sec.ports")}</span><span class="v na">${t("na")}</span></div>`;

  const gpuBlock = Array.isArray(gpu.adapters) && !gpu.adapters.length
    ? `<div class="kv"><span class="k">${t("k.adapter")}</span><span class="v na">${t("gpu.none")}</span></div>`
    : gpu.adapters
    ? gpu.adapters.map((a) => `${kv(t("k.adapter"), a.name)}${kv(t("k.manufacturer"), a.manufacturer)}${kv(t("k.driver"), a.driver_version)}${kv(t("k.vram"), fmtBytes(a.adapter_ram_bytes))}${kv(t("k.load"), a.usage_percent, " %")}${kv(t("k.temp"), a.temperature_celsius, " °C")}`).join('<div class="kv"></div>')
    : `<div class="kv"><span class="k">${t("k.adapter")}</span><span class="v na">${t("na")}</span></div>`;

  const tempBlock = temp.sensors
    ? temp.sensors.map((s) => `<div class="kv"><span class="k">${esc(s.label || s.chip || t("k.sensors"))}</span><span class="v mono">${esc(s.current_celsius)} °C</span></div>`).join("")
    : `<div class="kv"><span class="k">${t("k.sensors")}</span><span class="v na">${t("na.sensors")}</span></div>`;

  $("#device-content").innerHTML = `
    <div class="detail-grid">
      <div class="panel">
        <div class="panel-head"><div><h3>${t("sec.cpu")}</h3></div></div>
        ${kv(t("k.model"), cpu.model)}
        ${kv(t("k.manufacturer"), cpu.manufacturer)}
        ${kv(t("k.cores"), cpu.physical_cores)}
        ${kv(t("k.threads"), cpu.logical_processors)}
        ${kv(t("k.frequency"), cpu.frequency_MHz ? (cpu.frequency_MHz / 1000).toFixed(2) : null, " ГГц")}
        ${kv(t("k.load"), cpu.usage_percent, " %")}
      </div>
      <div class="panel">
        <div class="panel-head"><div><h3>${t("sec.gpu")}</h3></div></div>
        ${gpuBlock}
        <div class="hint">${t("hint.gpu")}</div>
      </div>
      <div class="panel">
        <div class="panel-head"><div><h3>${t("sec.temp")}</h3></div></div>
        ${tempBlock}
        <div class="hint">${temp.sensors ? t("hint.tempOk") : t("hint.tempNone")}</div>
      </div>
      <div class="panel wide">
        <div class="panel-head"><div><h3>${t("sec.ports")}</h3><div class="sub">${t("sec.portsSub")}</div></div></div>
        ${portsBlock}
      </div>
      <div class="panel wide">
        <div class="panel-head"><div><h3>${t("sec.net")}</h3><div class="sub">${t("sec.netSub")}</div></div></div>
        <table>${ifaceHead}<tbody>${interfaces}</tbody></table>
        ${otherBlock}
      </div>
      <div class="panel">
        <div class="panel-head"><div><h3>${t("sec.mem")}</h3></div></div>
        ${kv(t("k.total"), fmtBytes(ram.total_bytes))}
        ${kv(t("k.used"), fmtBytes(ram.used_bytes))}
        ${kv(t("k.free"), fmtBytes(ram.available_bytes))}
        ${kv(t("k.load"), ram.usage_percent, " %")}
      </div>
      <div class="panel wide">
        <div class="panel-head"><div><h3>${t("sec.disks")}</h3><div class="sub">${t("sec.disksSub")}</div></div></div>
        <table><thead><tr><th>${t("k.partition")}</th><th>${t("k.fs")}</th><th>${t("k.size")}</th><th>${t("k.occupied")}</th><th>${t("k.load")}</th></tr></thead><tbody>${partitions}</tbody></table>
        <div style="display:flex;gap:26px;margin-top:12px">
          <div class="kv" style="flex:1"><span class="k">${t("k.read")}</span><span class="v mono">${esc(fmtSpeed(io.read_speed_Bps) ?? "—")}</span></div>
          <div class="kv" style="flex:1"><span class="k">${t("k.write")}</span><span class="v mono">${esc(fmtSpeed(io.write_speed_Bps) ?? "—")}</span></div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head"><div><h3>${t("sec.bios")}</h3></div></div>
        ${kv(t("k.biosVersion"), bios.version)}
        ${kv(t("k.biosVendor"), bios.manufacturer)}
        ${kv(t("k.release"), bios.release_date)}
        ${kv(t("k.serial"), bios.serial_number)}
        ${kv(t("k.board"), (bios.motherboard || {}).model)}
        ${kv(t("k.boardVendor"), (bios.motherboard || {}).manufacturer)}
      </div>
      <div class="panel">
        <div class="panel-head"><div><h3>${t("sec.system")}</h3></div></div>
        ${kv(t("k.hostname"), system.hostname)}
        ${kv(t("k.os"), device.os_name ? `${device.os_name} ${device.os_version ?? ""}`.trim() : null)}
        ${kv(t("k.arch"), system.architecture)}
        ${kv(t("k.manufacturer"), system.manufacturer)}
        ${kv(t("k.model"), system.model)}
        ${kv(t("k.uptime"), fmtUptime(system.uptime_seconds))}
        ${kv(t("k.registered"), fmtTime(device.created_at))}
      </div>
    </div>`;
}

async function renderDevicePage(deviceId) {
  try {
    const [device, metrics] = await Promise.all([
      fetchJson(`/api/devices/${deviceId}`),
      fetchJson(`/api/devices/${deviceId}/metrics?limit=1`),
    ]);
    setServerPill(true);
    renderDevice(device, metrics.length ? metrics[0].payload : null);
  } catch {
    setServerPill(false);
    $("#dev-hostname").textContent = t("dev.loadError");
    $("#device-content").innerHTML = `<div class="state-box">${t("state.loadError")}<button class="btn" onclick="renderDevicePage(${deviceId})">${t("state.retry")}</button></div>`;
  }
}

/* ---------- алерты ---------- */
let alertsFilter = "ALL";

async function renderAlerts() {
  let alerts, devices;
  try {
    [alerts, devices] = await Promise.all([
      fetchJson(`/api/monitoring/alerts?limit=200`),
      fetchJson(`/api/devices`),
    ]);
    setServerPill(true);
  } catch {
    setServerPill(false);
    return;
  }
  const names = Object.fromEntries(devices.map((d) => [d.id, d.hostname]));
  const box = $("#alerts-box");
  if (!box) return;
  const subtitle = $("#page-subtitle");
  if (subtitle) subtitle.textContent = t("alerts.openCount", { n: alerts.filter((a) => a.status === "OPEN").length, m: alerts.length });

  const visible = alerts.filter((a) => alertsFilter === "ALL" || a.status === alertsFilter);
  if (!visible.length) {
    box.innerHTML = `<div class="state-box">${alerts.length ? t("alerts.emptyFilter") : t("alerts.empty")}</div>`;
    return;
  }
  box.innerHTML = `<table>
    <thead><tr><th>${t("th.time")}</th><th>${t("th.device")}</th><th>${t("th.level")}</th><th>${t("th.message")}</th><th>${t("th.status")}</th></tr></thead>
    <tbody>${visible.map((a) => `<tr>
      <td class="mono" style="color:var(--muted)">${esc(fmtTime(a.created_at))}</td>
      <td>${esc(names[a.device_id] ?? `ID ${a.device_id ?? "?"}`)}</td>
      <td>${a.severity === "CRITICAL" ? badge("crit", t("b.critical")) : badge("warn", t("b.warning"))}</td>
      <td>${esc(a.message)}</td>
      <td>${a.status === "OPEN" ? badge("crit", t("b.open")) : badge("ok", t("b.resolved"))}</td>
    </tr>`).join("")}</tbody></table>`;
}

/* ---------- события ---------- */
const EVENT_KEYS = {
  METRIC_STATUS_CHANGED: "event.METRIC_STATUS_CHANGED",
  HEALTH_CHANGED: "event.HEALTH_CHANGED",
  DEVICE_OFFLINE: "event.DEVICE_OFFLINE",
  DEVICE_ONLINE: "event.DEVICE_ONLINE",
};

function describeEvent(event) {
  const payload = event.payload || {};
  if (event.event_type === "METRIC_STATUS_CHANGED")
    return `${esc((payload.metric || "?").toUpperCase())}: ${esc(payload.from ?? "?")} → <b style="color:var(--accent)">${esc(payload.to ?? "?")}</b>`;
  if (event.event_type === "HEALTH_CHANGED")
    return `${t("ev.health")} <b style="color:var(--accent)">${esc(payload.health ?? "?")}</b>`;
  if (event.event_type === "DEVICE_OFFLINE")
    return `${t("ev.lastActivity")} ${esc(fmtTime(payload.last_seen))}`;
  return "";
}

async function renderEvents() {
  let events, devices;
  try {
    [events, devices] = await Promise.all([
      fetchJson(`/api/monitoring/events?limit=200`),
      fetchJson(`/api/devices`),
    ]);
    setServerPill(true);
  } catch {
    setServerPill(false);
    return;
  }
  const names = Object.fromEntries(devices.map((d) => [d.id, d.hostname]));
  const box = $("#events-box");
  if (!box) return;
  if (!events.length) {
    box.innerHTML = `<div class="state-box">${t("events.empty")}</div>`;
    return;
  }
  const tone = {
    METRIC_STATUS_CHANGED: "warn",
    HEALTH_CHANGED: "neutral",
    DEVICE_OFFLINE: "off",
    DEVICE_ONLINE: "ok",
  };
  box.innerHTML = `<table>
    <thead><tr><th>${t("th.time")}</th><th>${t("th.device")}</th><th>${t("th.event")}</th><th>${t("th.details")}</th></tr></thead>
    <tbody>${events.map((e) => `<tr>
      <td class="mono" style="color:var(--muted)">${esc(fmtTime(e.created_at))}</td>
      <td>${esc(names[e.device_id] ?? `ID ${e.device_id ?? "?"}`)}</td>
      <td>${badge(tone[e.event_type] || "neutral", esc(t(EVENT_KEYS[e.event_type] || e.event_type)))}</td>
      <td>${describeEvent(e)}</td>
    </tr>`).join("")}</tbody></table>`;
}

/* ---------- аналитика ---------- */
let analyticsDeviceId = null;

async function renderAnalytics() {
  const select = $("#device-select");
  if (!select) return;
  if (!analyticsDeviceId) {
    const devices = await fetchJson("/api/devices");
    setServerPill(true);
    if (!devices.length) {
      $("#chart-box").innerHTML = `<div class="state-box">${t("state.noDevices")}</div>`;
      return;
    }
    select.innerHTML = devices
      .map((d) => `<option value="${d.id}">${esc(d.hostname)}</option>`)
      .join("");
    analyticsDeviceId = devices[0].id;
  }
  const metrics = await fetchJson(`/api/devices/${analyticsDeviceId}/metrics?limit=240`);
  const box = $("#chart-box");
  if (!metrics.length) {
    box.innerHTML = `<div class="state-box">${t("state.noHistory")}</div>`;
    return;
  }
  const chronological = [...metrics].reverse(); // старые → новые
  const diskValue = (m) => {
    const parts = m.payload?.disk?.partitions;
    if (Array.isArray(parts) && parts.length) {
      const values = parts.map((p) => p.usage_percent).filter((v) => typeof v === "number");
      if (values.length) return Math.max(...values);
    }
    return null;
  };
  const series = [
    { name: t("chart.cpu"), color: "var(--accent)", values: chronological.map((m) => m.payload?.cpu?.usage_percent ?? null) },
    { name: t("chart.ram"), color: "var(--violet)", values: chronological.map((m) => m.payload?.ram?.usage_percent ?? null) },
    { name: t("chart.disk"), color: "var(--warn)", values: chronological.map(diskValue) },
  ];
  const times = chronological.map((m) => m.collected_at);
  box.innerHTML = lineChartSVG(series, times);
  box.innerHTML += `<div class="hint" style="margin-top:10px">${t("analytics.range", {
    from: esc(fmtTime(times[0])),
    to: esc(fmtTime(times[times.length - 1])),
    n: times.length,
  })}</div>`;
}

function lineChartSVG(series, times) {
  const width = 1100, height = 280, padL = 42, padR = 12, padT = 12, padB = 26;
  const innerW = width - padL - padR, innerH = height - padT - padB;
  const count = times.length;
  const x = (i) => padL + (count === 1 ? innerW / 2 : (i * innerW) / (count - 1));
  const y = (v) => padT + innerH - (Math.min(Math.max(v, 0), 100) / 100) * innerH;
  let grid = "";
  for (const mark of [0, 25, 50, 75, 100]) {
    grid += `<line x1="${padL}" x2="${width - padR}" y1="${y(mark)}" y2="${y(mark)}" stroke="var(--border)" stroke-dasharray="3 6"/>
             <text x="${padL - 8}" y="${y(mark) + 4}" fill="var(--muted)" font-size="11" text-anchor="end" font-family="var(--mono)">${mark}</text>`;
  }
  const timeTicks = [0, Math.floor((count - 1) / 2), count - 1]
    .filter((i, pos, arr) => arr.indexOf(i) === pos && times[i])
    .map((i) => `<text x="${x(i)}" y="${height - 6}" fill="var(--muted)" font-size="11" text-anchor="middle" font-family="var(--mono)">${esc(new Date(times[i]).toLocaleTimeString(LOCALES[lang], { hour12: false }))}</text>`)
    .join("");
  const lines = series.map((s) => {
    const segments = [];
    let current = [];
    s.values.forEach((v, i) => {
      if (v === null || v === undefined) {
        if (current.length > 1) segments.push(current);
        current = [];
      } else current.push([x(i), y(v)]);
    });
    if (current.length > 1) segments.push(current);
    const paths = segments
      .map((seg) => `M${seg.map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`).join(" L")}`)
      .join('" /><path d="');
    return paths
      ? `<path d="${paths}" fill="none" stroke="${s.color}" stroke-width="2.2"/>`
      : "";
  }).join("");
  const legend = series
    .map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`)
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;display:block">
    ${grid}${timeTicks}${lines}
  </svg>
  <div class="legend" style="margin-top:8px">${legend}</div>`;
}

/* ---------- настройки ---------- */
async function renderSettings() {
  const thresholdsBox = $("#thresholds-box");
  const systemBox = $("#system-box");
  if (!thresholdsBox || !systemBox) return;
  const [devices, config] = await Promise.all([
    fetchJson("/api/devices"),
    fetchJson("/api/monitoring/config"),
  ]);
  setServerPill(true);
  const rows = [
    [t("set.cpu"), "80 %", "95 %"],
    [t("set.ram"), "80 %", "95 %"],
    [t("set.disk"), "85 %", "95 %"],
    [t("set.temp"), t("set.notSet"), t("set.notSet")],
    [t("set.net"), t("set.notSet"), t("set.notSet")],
  ];
  thresholdsBox.innerHTML = `<table>
    <thead><tr><th>${t("set.metric")}</th><th>${t("set.warnFrom")}</th><th>${t("set.critFrom")}</th></tr></thead>
    <tbody>${rows.map(([name, warn, crit]) => `<tr>
      <td>${esc(name)}</td><td class="mono">${esc(warn)}</td><td class="mono">${esc(crit)}</td>
    </tr>`).join("")}</tbody></table>`;
  systemBox.innerHTML = `
    <div class="kv"><span class="k">${t("set.server")}</span><span class="v">FastAPI · stage 9</span></div>
    <div class="kv"><span class="k">${t("set.db")}</span><span class="v">SQLite</span></div>
    <div class="kv"><span class="k">${t("set.poll")}</span><span class="v">5 s (+~9 s)</span></div>
    <div class="kv"><span class="k">${t("set.offlineAfter")}</span><span class="v">${config.offline_after_seconds} s</span></div>
    <div class="kv"><span class="k">${t("set.confirm")}</span><span class="v">${config.confirmation_samples}</span></div>
    <div class="kv"><span class="k">${t("set.retention")}</span><span class="v">${config.retention_hours} h</span></div>
    <div class="kv"><span class="k">${t("set.refresh")}</span><span class="v">${config.dashboard_refresh_seconds} s</span></div>
    <div class="kv"><span class="k">${t("set.devices")}</span><span class="v">${devices.length}</span></div>`;
  renderAddressBox(systemBox);
}

async function renderAddressBox(container) {
  const info = await fetchJson("/api/monitoring/server-address");
  const box = document.createElement("div");
  box.className = "addr-box";
  box.innerHTML = `
    <div class="kv"><span class="k">${t("set.address")}</span><span class="v mono">${esc(info.url || t("set.noData"))}</span></div>
    <div style="display:flex;gap:8px;margin-top:6px">
      <input id="server-address-input" class="text-input mono" placeholder="${esc(info.detected || t("set.addressPh"))}" value="${esc(info.address || "")}">
      <button class="mini-btn" id="server-address-save">${t("set.save")}</button>
    </div>
    <div class="hint" style="margin-top:4px">${t("set.addressAuto")} · ${t("set.port")} ${esc(info.port)}</div>
    <div class="hint" style="margin-top:4px">${esc(t("set.firewall").replace("{port}", info.port))}</div>`;
  container.appendChild(box);
  const button = box.querySelector("#server-address-save");
  button.addEventListener("click", async function () {
    const value = box.querySelector("#server-address-input").value;
    try {
      await fetchJson("/api/monitoring/server-address", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: value }),
      });
      button.textContent = t("set.saved");
      setTimeout(renderSettings, 900);
    } catch {
      button.textContent = t("set.addressBad");
      setTimeout(function () { button.textContent = t("set.save"); }, 1500);
    }
  });
}

/* ---------- управление строкой: кнопки ---------- */
document.addEventListener("click", (event) => {
  if (event.target.closest("#add-device-btn")) { event.stopPropagation(); openPairingModal(); return; }
  if (event.target.closest("#pairing-close")) { document.getElementById("modal-root").innerHTML = ""; pairingModalOpen = false; return; }
  const approveBtn = event.target.closest("button[data-pair-approve]");
  if (approveBtn) {
    event.stopPropagation();
    pairDecision(approveBtn.dataset.pairApprove, "approve");
    return;
  }
  const rejectBtn = event.target.closest("button[data-pair-reject]");
  if (rejectBtn) {
    event.stopPropagation();
    pairDecision(rejectBtn.dataset.pairReject, "reject");
    return;
  }
  const refreshButton = event.target.closest("button[data-refresh]");
  if (refreshButton) {
    event.stopPropagation();
    refreshDeviceRow(refreshButton);
    return;
  }
  const autoButton = event.target.closest("button[data-auto]");
  if (autoButton) {
    event.stopPropagation();
    toggleDeviceAuto(autoButton);
    return;
  }
  const deleteButton = event.target.closest("button[data-delete]");
  if (deleteButton) {
    event.stopPropagation();
    deleteDevice(deleteButton);
    return;
  }
  if (event.target.closest("button, a")) return;
  const row = event.target.closest("tr[data-href]");
  if (row) window.location.href = row.dataset.href;
});

/* ---------- pairing: «＋ Добавить компьютер» ---------- */
let pairingModalOpen = false;

async function openPairingModal() {
  if (pairingModalOpen) return;
  try {
    await fetchJson("/api/monitoring/pairing", { method: "POST" });
  } catch {
    setServerPill(false);
    return;
  }
  pairingModalOpen = true;
  // Кнопка «Добавить» теперь на всех страницах — окно опрашивает заявки само (на дашборде это делает его цикл).
  const pairingTimer = setInterval(function () {
    if (!pairingModalOpen) clearInterval(pairingTimer);
    else if (document.body.dataset.page !== "dashboard") updatePairingModal();
  }, 3000);
  fetchJson("/api/monitoring/config").then(function (cfg) {
    const urlEl = document.getElementById("pairing-url");
    if (urlEl && cfg.download_url) urlEl.textContent = cfg.download_url;
  }).catch(function () {});
  const root = document.getElementById("modal-root");
  if (!root) return;
  root.innerHTML = `<div class="modal-overlay"><div class="modal">
    <div class="panel-head">
      <div><h3>${t("pair.title")}</h3></div>
      <button class="mini-btn" id="pairing-close">${t("pair.close")}</button>
    </div>
    <div class="pair-hint">${t("pair.hint")}</div>
    <div class="pair-code-box">
      <div class="pair-code-label">${t("pair.codeLabel")}</div>
      <div class="pair-code mono" id="pairing-code">—</div>
      <div class="pair-expires">${t("pair.expires")} <span class="mono" id="pairing-expires">—</span></div>
      <button class="mini-btn" id="pairing-copy-code" style="margin-top:6px">${t("pair.copyCode")}</button>
    </div>
    <div class="pair-download">
      <div style="color:var(--muted);font-size:12px;margin-bottom:4px">${t("pair.downloadHint")}</div>
      <div class="mono" style="color:var(--accent);font-size:12.5px;overflow-wrap:anywhere" id="pairing-url"></div>
      <button class="mini-btn" id="pairing-copy" style="margin-top:6px">${t("pair.copy")}</button>
    </div>
    <h3 style="margin:12px 0 6px">${t("pair.pending")}</h3>
    <div id="pairing-pending"><div class="state-box">${t("pair.none")}</div></div>
  </div></div>`;
  await updatePairingModal();
}

async function updatePairingModal() {
  if (!pairingModalOpen) return;
  let records;
  try {
    records = await fetchJson("/api/monitoring/pairing");
    setServerPill(true);
  } catch {
    setServerPill(false);
    return;
  }
  if (!pairingModalOpen) return;
  if (!records.length) {
    // код истёк, пока окно открыто — молча выпускаем новый
    await fetchJson("/api/monitoring/pairing", { method: "POST" });
    records = await fetchJson("/api/monitoring/pairing");
    if (!records.length) return;
    const codeEl = document.getElementById("pairing-code");
    if (codeEl) codeEl.textContent = records[0].full_code || records[0].code;
  }
  const record = records[0];
  const codeEl = document.getElementById("pairing-code");
  if (codeEl && codeEl.textContent === "—") codeEl.textContent = record.full_code || record.code;
  const copyCodeBtn = document.getElementById("pairing-copy-code");
  if (copyCodeBtn && !copyCodeBtn.dataset.bound) {
    copyCodeBtn.dataset.bound = "1";
    copyCodeBtn.addEventListener("click", function () {
      navigator.clipboard.writeText(document.getElementById("pairing-code").textContent).then(function () {
        copyCodeBtn.textContent = t("pair.copied");
        setTimeout(function () { copyCodeBtn.textContent = t("pair.copyCode"); }, 1500);
      });
    });
  }
  const urlEl = document.getElementById("pairing-url");
  if (urlEl && !urlEl.textContent) {
    try {
      const info = await fetchJson("/api/monitoring/server-address");
      urlEl.textContent = info.url ? info.url + "/download" : t("set.noData");
    } catch { urlEl.textContent = t("set.noData"); }
  }
  const copyBtn = document.getElementById("pairing-copy");
  if (copyBtn && !copyBtn.dataset.bound) {
    copyBtn.dataset.bound = "1";
    copyBtn.addEventListener("click", function () {
      const url = document.getElementById("pairing-url").textContent;
      navigator.clipboard.writeText(url).then(function () {
        copyBtn.textContent = t("pair.copied");
        setTimeout(function () { copyBtn.textContent = t("pair.copy"); }, 1500);
      });
    });
  }
  const expEl = document.getElementById("pairing-expires");
  if (expEl && record.expires_at) {
    const left = Math.max(0, Math.round((new Date(parseLocal(record.expires_at)) - Date.now()) / 1000));
    expEl.textContent = Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
  }
  const box = document.getElementById("pairing-pending");
  if (!box) return;
  if (!record.device) {
    box.innerHTML = `<div class="state-box">${t("pair.none")}</div>`;
    return;
  }
  const device = record.device;
  box.innerHTML = `<div class="pending-device">
    <div class="dev-name">${esc(device.hostname)} <span class="mono" style="color:var(--muted)">${esc(device.ip_address ?? "")}</span></div>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="mini-btn auto on" data-pair-approve="${esc(record.code)}">${t("pair.approve")}</button>
      <button class="mini-btn danger" data-pair-reject="${esc(record.code)}">${t("pair.reject")}</button>
    </div>
  </div>`;
}

function parseLocal(iso) {
  return /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
}

async function pairDecision(code, action) {
  try {
    await fetchJson(`/api/monitoring/pairing/${code}/${action}`, { method: "POST" });
  } catch {
    setServerPill(false);
    return;
  }
  if (action === "approve") {
    // Компьютер принят — окно «Добавить» закрываем, список обновляем.
    pairingModalOpen = false;
    const root = document.getElementById("modal-root");
    if (root) root.innerHTML = "";
    const render = PAGE_RENDERERS[document.body.dataset.page];
    if (render) await render();
    return;
  }
  await updatePairingModal();
}

/* ---------- запуск ---------- */
const PAGE_RENDERERS = {
  dashboard: renderDashboard,
  devices: renderDevices,
  alerts: renderAlerts,
  events: renderEvents,
  analytics: renderAnalytics,
  settings: renderSettings,
};

applyI18n();
ensureConnBanner();
const page = document.body.dataset.page;
if (page === "dashboard") {
  schedule(renderDashboard);
} else if (page === "devices") {
  schedule(renderDevices);
} else if (page === "device") {
  const deviceId = Number(document.body.dataset.deviceId);
  schedule(() => renderDevicePage(deviceId));
} else if (page === "alerts") {
  schedule(renderAlerts);
  document.addEventListener("click", (event) => {
    const chip = event.target.closest("#alerts-filter-wrap .chip");
    if (!chip) return;
    alertsFilter = chip.dataset.filter;
    document.querySelectorAll("#alerts-filter-wrap .chip").forEach((c) =>
      c.classList.toggle("active", c === chip)
    );
    renderAlerts();
  });
} else if (page === "events") {
  schedule(renderEvents);
} else if (page === "analytics") {
  schedule(renderAnalytics);
  document.addEventListener("change", (event) => {
    if (event.target.id === "device-select") {
      analyticsDeviceId = Number(event.target.value);
      renderAnalytics();
    }
  });
} else if (page === "settings") {
  renderSettings();
}

= Verimor Connector =

Integrates Verimor's SMS gateway, Bulutsantralim PBX API and
IYS (İleti Yönetim Sistemi) consent management into Odoo 18's
native communication stack.

Features
--------
* Route all outgoing SMS through Verimor's v2 API with IYS filtering
* Push IYS consent records (MESAJ / ARAMA / EPOSTA) upon partner save
* Block commercial e-mails for partners with IYS e-mail rejection
* Click-to-call from res.partner form view via Bulutsantralim API
* Incoming call popup via Odoo bus (WebSocket)
* Full call event log (verimor.call.log)
* Two webhook endpoints: /verimor/call/event and /verimor/call/advisory

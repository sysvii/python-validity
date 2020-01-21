from proto97.flash import read_flash

def open97(usb, tls):
    usb.open()
    usb.send_init()

    # try to init TLS session from the flash
    tls.parseTlsFlash(read_flash(1, 0, 0x1000))

    tls.open()

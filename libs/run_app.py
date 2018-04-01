
def reset_and_run(path):
	import pyb
#	if stm.mem8[0x40002850] == 0:   # this battery backed RAM section is set to 0 when the name screen runs
	with open('main.json', 'w') as f:
		f.write('{"main":"' + path + '"}')
#		stm.mem8[0x40002850] = 2    #set this address to != 0 so this if statement doesnt run next time
	pyb.hard_reset()

def run_app(path):
	import buttons
	import ugfx
	import sys

	buttons.init()
	ugfx.init()
	ugfx.clear()

	if not buttons.has_interrupt("BTN_MENU"):
		buttons.enable_menu_reset()

	try:
		# Make libraries shipped by the app importable
		app_path = '/flash/' + '/'.join(path.split('/')[:-1])
		sys.path.append(app_path)

		mod = __import__(path)
		if "main" in dir(mod):
			mod.main()
	except Exception as e:
		import sys
		import uio
		import ugfx
		s = uio.StringIO()
		sys.print_exception(e, s)
		ugfx.clear()
		ugfx.set_default_font(ugfx.FONT_SMALL)
		w=ugfx.Container(0,0,ugfx.width(),ugfx.height())
		ugfx.Label(0,0,ugfx.width(),ugfx.height(),s.getvalue(),parent=w)
		w.show()
		raise(e)
	import stm
	stm.mem8[0x40002850] = 0x9C
	import pyb
	pyb.hard_reset()

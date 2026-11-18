import ctypes as C
E=C.CDLL('libEGL.so.1'); G=C.CDLL('libGL.so.1')
def e(name,ret,*args):
 f=getattr(E,name);f.restype=ret;f.argtypes=list(args);return f
getdisplay=e('eglGetPlatformDisplay',C.c_void_p,C.c_uint,C.c_void_p,C.POINTER(C.c_int))
initialize=e('eglInitialize',C.c_uint,C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int))
choose=e('eglChooseConfig',C.c_uint,C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int))
bind=e('eglBindAPI',C.c_uint,C.c_uint)
ctxcreate=e('eglCreateContext',C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int))
pbuffer=e('eglCreatePbufferSurface',C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int))
current=e('eglMakeCurrent',C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p)
D=getdisplay(0x31DD,None,None);major=C.c_int();minor=C.c_int();assert initialize(D,C.byref(major),C.byref(minor))
attrs=(C.c_int*13)(0x3033,1,0x3040,8,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
config=C.c_void_p();n=C.c_int();assert choose(D,attrs,C.byref(config),1,C.byref(n)) and n.value;assert bind(0x30A2)
context=ctxcreate(D,config,None,(C.c_int*1)(0x3038));assert context
surface=pbuffer(D,config,(C.c_int*5)(0x3057,756,0x3056,1008,0x3038));assert surface
assert current(D,surface,surface,context)
G.glGetString.argtypes=[C.c_uint];G.glGetString.restype=C.c_char_p
print('GL',G.glGetString(0x1F02),G.glGetString(0x1F01))

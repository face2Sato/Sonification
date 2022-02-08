import("stdfaust.lib");

f = 440;
// gate = button("note on");
gate = 1;
r1 = hslider("L1",0,0,10,1);
l1 = hslider("R1",0,0,10,1);
r2 = hslider("L2",0,0,10,1);
r3 = hslider("L3",0,0,10,1);
l2 = hslider("R2",0,0,10,1);
l3 = hslider("R3",0,0,10,1);
// amp = hslider("amp",1,0,1,0.01);
amp = 1;
adsr = en.adsr(0,0,0.8,0.5,gate); //adsr(at,dt,sl,rt,gate) : _


operator(f, index, amp, adsr, phase) = os.oscp(f*index, phase) * amp * adsr;


carrier1 = operator(f, r1, amp, adsr);
carrier3 = operator(f, l1, amp, adsr);
mod1 = operator(f, r2, amp, adsr);
mod2 = operator(f, r3, amp, adsr);
mod3 = operator(f, l2, amp, adsr);
mod4 = operator(f, l3, amp, adsr);

//another algorythm
//process = _ <: ((mod5 , mod4), (mod3, mod2)) :> mod1 : carrier <: _, _;
process = _ <: ( (mod2 : mod1 : carrier1),/*L*/(mod4 : mod3 : carrier3)) ;/*R*/



//<:_,_ はLRに出力できる
import("stdfaust.lib");

A_4=440;

//flin_min<=fc_linear,fm_linear<=flin_max
//envlin_min<=env_linear<=envlin_max

flin_min = -36;
flin_max = 60;
envlin_min = 0;
envlin_max= 1;

fc_linear = hslider("fc_index",flin_min,flin_min,flin_max,0.01);
fm_linear = hslider("fm_index",flin_min,flin_min,flin_max,0.01);
env_linear = hslider("env_linear",envlin_min,envlin_min,envlin_max,0.01);

//fc: carrier freq, fm...modulation freq, env...envelope (control amplitude)
fc = A_4 * pow(2,fc_linear/12);

fm = A_4 * pow(2,fm_linear/12);

//used default feature of Faust to calculate non linear gain
env = ba.lin2LogGain(env_linear);

//define FM operator imitating Yamaha DX7
operator(fc, fm, env)= os.oscp(fc, os.osc(fm)) * env;

//https://github.com/grame-cncm/faustlibraries/blob/master/oscillators.lib
//oscp(freq,phase) = oscsin(freq) * cos(phase) + osccos(freq) * sin(phase)
//thus, oscp(freq,phase) = oscsin(freq +  oscsin(phase))

module = (operator(fc,fm,env));

process = module <:_,_;                                                                 



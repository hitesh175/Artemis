'use strict';
const vertexSource = `#version 300 es
in vec2 a; out vec2 uv;
void main(){uv=a*.5+.5;gl_Position=vec4(a,0.,1.);}`;
// Analytical field: no ray marching, nested material sampling, or textures.
const fragmentSource = `#version 300 es
precision highp float;
in vec2 uv;out vec4 outColor;
uniform vec2 res;
uniform float t,crystal,water,motion,state;
void main(){
 vec2 p=(uv-.5)*2.;p.x*=res.x/res.y;
 float r=length(p),a=atan(p.y,p.x);
 float clock=t*.19;
 float shape=.64+.012*sin(a*3.+clock)+.008*sin(a*5.-clock*.7);
 float d=r-shape;
 float flow=.5+.5*sin(a*3.-clock*2.+sin(a*5.+clock)*.5);
 vec3 blue=vec3(.24,.53,1.);vec3 violet=vec3(.63,.33,1.);
 vec3 hue=mix(blue,violet,.5+.5*sin(a+clock*.4));
 hue=mix(hue,vec3(.27,.86,.86),clamp(state,0.,.55)*.45);
 float rim=exp(-abs(d)*115.);
 float ribbon=exp(-abs(d-.018*sin(a*7.-clock))*58.);
 float halo=exp(-abs(d)*16.)*.26;
 float outer=exp(-abs(d)*5.)*.08;
 float energy=.65+.35*flow;
 vec3 light=hue*(rim*1.5+ribbon*.38+halo+outer)*energy;
 light+=vec3(.65,.83,1.)*pow(flow,10.)*rim*.55;
 float core=1.-smoothstep(shape-.025,shape+.005,r);
 vec3 coreColor=vec3(.013,.018,.034)+hue*pow(clamp(r/shape,0.,1.),6.)*.018;
 float alpha=max(core,clamp((rim+ribbon*.3+halo+outer)*1.3,0.,1.));
 vec3 col=mix(light,coreColor,core);
 col+=hue*rim*.65*(.9+.1*(crystal+water));
 outColor=vec4(col,alpha);
}`;

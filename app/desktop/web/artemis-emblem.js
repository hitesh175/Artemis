'use strict';
const vertexSource=`#version 300 es
in vec2 a;out vec2 uv;void main(){uv=a*.5+.5;gl_Position=vec4(a,0.,1.);}`;
// Stable crescent-blade A; animated illumination only, no ray marching.
const fragmentSource=`#version 300 es
precision highp float;
in vec2 uv;out vec4 outColor;
uniform vec2 res;uniform float t,crystal,water,motion,state;
float segment(vec2 p,vec2 a,vec2 b){vec2 ab=b-a;return length(p-a-ab*clamp(dot(p-a,ab)/dot(ab,ab),0.,1.));}
float blade(vec2 p,float side){
 float v=clamp((.72-p.y)/1.37,0.,1.);
 float spine=side*(.018+.49*v-.14*sin(v*3.14159));
 float width=.012+.073*sin(v*3.14159)+.022*v;
 return max(abs(p.x-spine)-width,max(p.y-.72,-.65-p.y));
}
float emblem(vec2 p){
 float left=blade(p,-1.),right=blade(p,1.);
 float cross=segment(p,vec2(-.21,-.20),vec2(.25,-.10))-.025;
 return min(min(left,right),cross);
}
void main(){
 vec2 p=(uv-.5)*2.;p.x*=res.x/res.y;
 float d=emblem(p);
 vec3 ice=vec3(.52,.77,1.),silver=vec3(.86,.92,1.),warm=vec3(1.,.88,.65);
 float breath=.94+.06*sin(t*.8);
 if(d>0.){float glow=(exp(-d*62.)*.20+exp(-d*16.)*.025)*breath;outColor=vec4(ice,glow);return;}
 float h=.002;vec2 grad=vec2(emblem(p+vec2(h,0))-emblem(p-vec2(h,0)),emblem(p+vec2(0,h))-emblem(p-vec2(0,h)))/(2.*h);
 float bevel=exp(d*40.);
 vec3 n=normalize(vec3(grad*bevel*.85,1.));
 float light=max(dot(n,normalize(vec3(-.6,.7,.9))),0.);
 float spec=pow(max(dot(n,normalize(vec3(-.4,.6,1.))),0.),22.);
 vec3 col=mix(vec3(.16,.25,.38),silver,light*.76)+silver*spec*.55;
 float stream=pow(.5+.5*sin(p.y*10.-t*.9+p.x*9.+sin(p.y*3.+t*.2)),12.);
 float thread=exp(-pow((p.x+.16*sin(p.y*4.-t*.25))/.025,2.));
 col+=mix(ice,warm,smoothstep(-.2,.65,p.y))*(stream*.26+thread*.20)*breath;
 col+=silver*bevel*.25;
 col+=ice*state*.07;
 outColor=vec4(col,1.-smoothstep(-.004,0.,d));
}`;

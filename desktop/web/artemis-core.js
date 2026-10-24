'use strict';
const vertexSource=`#version 300 es
in vec2 a;out vec2 uv;void main(){uv=a*.5+.5;gl_Position=vec4(a,0.,1.);}`;
// Sculpted translucent lens with advected internal ribbons; no ray marching.
const fragmentSource=`#version 300 es
precision highp float;
in vec2 uv;out vec4 outColor;
uniform vec2 res;uniform float t,crystal,water,motion,state;
float band(float v,float w){return exp(-v*v/(w*w));}
void main(){
 vec2 p=(uv-.5)*2.;p.x*=res.x/res.y;
 float clock=t*.23;
 float a=atan(p.y,p.x),r=length(p);
 float shape=.63+.067*sin(3.*a+clock*.45)+.032*cos(2.*a-clock*.31);
 vec2 q=p/vec2(.87,1.10);
 float d=length(q)/shape;
 float edge=1.-d;
 vec3 ice=vec3(.56,.77,1.),silver=vec3(.83,.89,.96),gold=vec3(.94,.76,.48);
 if(edge<0.){float glow=exp(edge*65.)*.17+exp(edge*18.)*.028;outColor=vec4(mix(ice,silver,.4),glow);return;}
 float z=sqrt(max(0.,1.-d*d));
 vec3 n=normalize(vec3(q/shape,z));
 float u=q.x+.12*sin(q.y*4.+clock)+.055*sin(q.y*8.-clock*.7);
 float v=q.y+.07*sin(q.x*5.-clock*.5);
 float ribbonA=band(u+.19*sin(v*3.+clock*.5)-.11,.044);
 float ribbonB=band(u-.23*sin(v*3.7-clock*.4)+.16,.032);
 float ribbonC=band(v-.32*sin(u*4.+clock*.3),.025)*.42;
 float inner=(ribbonA+ribbonB)*(.52+.48*z)+ribbonC;
 float rim=pow(1.-z,2.5);
 float key=pow(max(dot(n,normalize(vec3(-.8,.7,1.))),0.),18.);
 float reflected=band(n.x+.42+.10*sin(n.y*3.),.12)*.55;
 float caustic=band(u+.17*sin(v*4.-clock*.6),.015)*.6;
 vec3 tint=mix(ice,gold,smoothstep(-.35,.5,v+u*.7));
 float crescent=pow(1.-z,1.8)*smoothstep(-.5,.6,-n.x+n.y*.45); float broad=pow(max(dot(n,normalize(vec3(-.6,.65,1.))),0.),2.); vec3 col=mix(vec3(.13,.21,.32),silver*.57,broad)+silver*(rim*.43+reflected*.65+key*.72)+silver*crescent*.8;
 col+=tint*inner*(.38+.22*(crystal+water));
 col+=silver*caustic*.26+ice*rim*.25;
 col+=mix(ice,vec3(.6,.95,.9),clamp(state,0.,1.))*inner*.06;
 float mask=smoothstep(0.,.012,edge);
 col=pow(max(col,vec3(0.)),vec3(.82)); float alpha=(.92+rim*.06)*mask;
 outColor=vec4(col,clamp(alpha,0.,.98));
}`;


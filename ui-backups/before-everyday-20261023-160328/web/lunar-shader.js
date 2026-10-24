'use strict';
const vertexSource=`#version 300 es
in vec2 a;out vec2 uv;void main(){uv=a*.5+.5;gl_Position=vec4(a,0.,1.);}`;
// An analytical sphere with procedural lunar relief. No ray marching.
const fragmentSource=`#version 300 es
precision highp float;
in vec2 uv;out vec4 outColor;
uniform vec2 res;uniform float t,crystal,water,motion,state;
float hash(vec3 p){p=fract(p*.3183099+vec3(.1,.2,.3));p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float terrain(vec3 p){return noise(p*3.)*.50+noise(p*8.)*.25+noise(p*23.)*.15+noise(p*65.)*.10;}
void main(){
 vec2 p=(uv-.5)*2.;p.x*=res.x/res.y;
 float radius=.70,r=length(p),edge=r-radius;
 vec3 silver=vec3(.72,.83,1.);
 if(r>radius){float halo=exp(-edge*28.)*.17+exp(-edge*8.)*.025;outColor=vec4(silver,halo*(1.-smoothstep(.16,.28,edge)));return;}
 vec2 xy=p/radius;vec3 n=vec3(xy,sqrt(max(0.,1.-dot(xy,xy))));
 float turn=.12+t*.009;float c=cos(turn),s=sin(turn);
 vec3 q=vec3(c*n.x+s*n.z,n.y,-s*n.x+c*n.z);
 float h=terrain(q*1.7),rough=noise(q*115.);
 float craters=0.;
 for(int i=0;i<15;i++){
  float k=float(i);vec3 center=normalize(vec3(sin(k*7.3+1.),cos(k*3.8+2.),sin(k*4.1+3.)));
  float d=length(q-center);float size=.035+.09*hash(vec3(k+1.));
  float rim=exp(-pow((d-size)/.013,2.));
  craters+=rim*.14-(1.-smoothstep(size*.25,size,d))*.14;
 }
 vec3 light=normalize(vec3(-.72,.48,.48));
 float diffuse=dot(n,light);
 float phase=smoothstep(-.13,.12,diffuse);
 float illumination=.045+phase*(.18+.72*max(diffuse,0.));
 float maria=smoothstep(.28,.68,h);
 vec3 material=mix(vec3(.29,.34,.43),vec3(.84,.85,.85),maria);
 material*=.82+rough*.28+craters;
 vec3 col=material*illumination;
 float fres=pow(1.-n.z,4.);
 col+=silver*fres*.12;
 col+=vec3(.95,.86,.69)*pow(max(diffuse,0.),8.)*.045;
 col+=vec3(.35,.57,.85)*clamp(state,0.,1.)*.025;
 float aa=1.-smoothstep(radius-.006,radius,r);
 outColor=vec4(col,aa);
}`;

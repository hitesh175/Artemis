'use strict';
(()=>{
 const byId=id=>document.getElementById(id);
 async function refresh(){
  try{const result=await window.pywebview?.api?.get_weather_location();if(result?.ok)byId('weather-location').textContent=result.location||'No city saved';}catch(err){console.error(err)}
 }
 byId('weather-find').addEventListener('click',async()=>{
  const list=byId('weather-choices'),button=byId('weather-find');button.disabled=true;list.textContent='Finding locations…';
  try{
   const result=await window.pywebview?.api?.find_weather_locations(byId('weather-city').value);
   if(!result?.ok)throw Error(result?.error||'Use the Artemis desktop app.');
   list.replaceChildren();
   if(!result.choices.length)list.textContent='No matching city. Include the country.';
   for(const choice of result.choices){
    const item=document.createElement('button');item.className='app-confirm';item.textContent='Use '+choice.name;
    item.addEventListener('click',async()=>{
     item.disabled=true;
     try{const saved=await window.pywebview.api.select_weather_location(choice.token);list.textContent=saved.reply;await refresh();}catch(err){list.textContent=err.message}
    });list.appendChild(item);
   }
  }catch(err){list.textContent=err.message}finally{button.disabled=false}
 });
 window.addEventListener('pywebviewready',refresh);void refresh();
})();

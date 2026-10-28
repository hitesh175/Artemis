'use strict';
(()=>{
  const results=document.getElementById('performance-results');
  const refresh=document.getElementById('refresh-performance');
  const clear=document.getElementById('clear-performance');
  const stages={chat:'Chat request',recognition:'Speech recognition',speech:'Speech output'};
  const fields={first_text_seconds:'First text',model_load_seconds:'Model loading',synthesis_seconds:'Voice generation',playback_seconds:'Playback',capture_seconds:'Recording and preparation',transcription_seconds:'Transcription'};
  let checking=false;
  async function update(erase=false){
    if(checking)return;
    checking=true;refresh.disabled=true;clear.disabled=true;
    try{
      const api=window.pywebview?.api;
      if(!api?.get_performance)throw Error('Open the updated desktop app to see timings.');
      if(erase){const result=await api.clear_performance();if(!result.ok)throw Error('Could not clear timings.');}
      const data=await api.get_performance();
      if(!data.ok)throw Error('Could not load timings.');
      results.replaceChildren();
      if(!data.retained){results.textContent='No timings yet this session. Use chat or voice, then refresh.';return;}
      for(const summary of data.summary){
        const line=document.createElement('p');
        if(!summary.latest){line.textContent=stages[summary.stage]+': no measurements yet.';}
        else{
          const latest=summary.latest;
          const details=Object.entries(fields).filter(([key])=>typeof latest[key]==='number')
            .map(([key,label])=>label+': '+latest[key].toFixed(2)+' s');
          line.textContent=stages[summary.stage]+': last '+latest.total_seconds.toFixed(2)+' s ('+latest.outcome+'). '+
            (summary.mean_seconds===null?'No completed samples.':'Completed average: '+summary.mean_seconds.toFixed(2)+' s from '+summary.completed+' samples.')+
            (details.length?'\n'+details.join(' · '):'');
        }
        results.appendChild(line);
      }
    }catch(error){results.textContent=error.message;}
    finally{checking=false;refresh.disabled=false;clear.disabled=false;}
  }
  refresh.addEventListener('click',()=>void update());
  clear.addEventListener('click',()=>void update(true));
})();

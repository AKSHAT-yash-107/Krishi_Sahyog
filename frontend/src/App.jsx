import React, {useEffect, useState} from 'react';
import {Sprout, LayoutDashboard, Leaf, FlaskConical, CloudSun, MessageCircle, Menu, Bell, ArrowUpRight, Upload, Send, MapPin, CheckCircle2, AlertCircle, LoaderCircle, Sun, Droplets, Wind, Satellite, BrainCircuit, BarChart3} from 'lucide-react';
import AdvisoryText from './components/AdvisoryText';
import MarkdownReport from './components/MarkdownReport';
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const nav = [{id:'overview',label:'Overview',icon:LayoutDashboard},{id:'disease',label:'Disease detection',icon:Leaf},{id:'soil',label:'Soil advisory',icon:FlaskConical},{id:'weather',label:'Weather advisory',icon:CloudSun},{id:'satellite',label:'Satellite imagery',icon:Satellite},{id:'mandi',label:'Mandi & selling strategy',icon:Sprout},{id:'intelligence',label:'Krishi Sahyog Intelligence',icon:BrainCircuit},{id:'assistant',label:'Farmer assistant',icon:MessageCircle}];

function App(){
 const [page,setPage]=useState('overview'),[mobile,setMobile]=useState(false);
 const [crop,setCrop]=useState('Wheat'),[location,setLocation]=useState('Bhopal, Madhya Pradesh');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState(null);
 const [file,setFile]=useState(null),[filePreview,setFilePreview]=useState(''),[soil,setSoil]=useState({nitrogen:'',phosphorus:'',potassium:'',ph:'',soil_type:'Not specified'});
 const [soilMode,setSoilMode]=useState('card'),[soilIrrigation,setSoilIrrigation]=useState('Rainfed');
 const [soilCardFile,setSoilCardFile]=useState(null),[ocrBusy,setOcrBusy]=useState(false),[ocrResult,setOcrResult]=useState(null);
 const [growth,setGrowth]=useState('Vegetative'),[question,setQuestion]=useState(''),[history,setHistory]=useState([]);
 const [satelliteInput,setSatelliteInput]=useState({latitude:'23.8388',longitude:'78.7378',radius_m:'500',start_date:'2026-09-01',end_date:'2026-11-04',max_cloud:'40'});
 const [polygonText,setPolygonText]=useState('');
  const [mandiForm,setMandiForm]=useState({state:'Madhya Pradesh',district:'',commodity:'Soyabean',variety:'',quantity_quintals:'50',transport_rate_per_quintal_km:'2',handling_cost_per_quintal:'20'});
  const [mandiMarkets,setMandiMarkets]=useState([]);
  const [nearestInfo,setNearestInfo]=useState(null);
  const [mandiDistances,setMandiDistances]=useState({});
  const [mandiLoading,setMandiLoading]=useState(false);
  const [mandiResult,setMandiResult]=useState(null);
  const [mandiError,setMandiError]=useState('');
  const [mandiFilters,setMandiFilters]=useState({states:[],districts:[],commodities:[],varieties:[]});
  const [mandiFiltersLoading,setMandiFiltersLoading]=useState(false);
  const [mandiPrices,setMandiPrices]=useState(null);
  const [mandiPricesLoading,setMandiPricesLoading]=useState(false);
  const [mandiPricesError,setMandiPricesError]=useState('');
  const [intelligenceForm,setIntelligenceForm]=useState({soil_type:'Not specified',nitrogen:'',phosphorus:'',potassium:'',ph:'',fetch_weather:true,fetch_satellite:false,latitude:satelliteInput.latitude,longitude:satelliteInput.longitude,radius_m:'500',start_date:'2026-09-01',end_date:'2026-11-04',max_cloud:'30'});
  const [intelligenceBusy,setIntelligenceBusy]=useState(false);
  const [intelligenceError,setIntelligenceError]=useState('');
  const [intelligenceResult,setIntelligenceResult]=useState(null);
  const [locationSuggestions,setLocationSuggestions]=useState([]);
  const [locationSearching,setLocationSearching]=useState(false);
  const [locationConfirmed,setLocationConfirmed]=useState(false);

  const selectedStateOption=mandiFilters.states.find(x=>x.name===mandiForm.state);
  const availableDistricts=mandiFilters.districts.filter(x=>!selectedStateOption||x.state_id===selectedStateOption.id);
  const selectedCommodityOption=mandiFilters.commodities.find(x=>x.name===mandiForm.commodity);
  const availableVarieties=mandiFilters.varieties.filter(x=>!x.commodity_id||!selectedCommodityOption||x.commodity_id===selectedCommodityOption.id);
  useEffect(()=>{
    let active=true;
    (async()=>{setMandiFiltersLoading(true);try{const response=await fetch(`${API}/api/mandi/filters`);const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not load local mandi filters');if(!active)return;setMandiFilters(data);
      setMandiForm(old=>({...old, state:data.states?.some(x=>x.name===old.state)?old.state:(data.states?.[0]?.name||old.state), commodity:data.commodities?.some(x=>x.name===old.commodity)?old.commodity:(data.commodities?.[0]?.name||old.commodity)}));
    }catch(err){if(active)setMandiError(err.message);}finally{if(active)setMandiFiltersLoading(false);}})();
    return ()=>{active=false;};
  },[]);
 useEffect(()=>{
  if(!file){setFilePreview('');return;}
  const url=URL.createObjectURL(file);
  setFilePreview(url);
  return ()=>URL.revokeObjectURL(url);
 },[file]);

 useEffect(()=>{
  if(!location.trim()||location.trim().length<3){setLocationSuggestions([]);return;}
  let active=true;
  const timer=setTimeout(async()=>{
   setLocationSearching(true);
   try{
    const r=await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(location)}&limit=5&lang=en`);
    if(!r.ok)throw new Error('Place search unavailable');
    const d=await r.json();
    if(active)setLocationSuggestions(d.features||[]);
   }catch{if(active)setLocationSuggestions([]);}
   finally{if(active)setLocationSearching(false);}
  },500);
  return ()=>{active=false;clearTimeout(timer);};
 },[location]);
 const reset=()=>{setError('');setResult(null)};
 async function request(path, options){
   setBusy(true);reset();
   try{const r=await fetch(API+path,options);const data=await r.json();if(!r.ok)throw new Error(data.detail||'Request failed');setResult(data);}
   catch(e){setError(e.message+' — Check that the backend is running and API keys are configured.');}
   finally{setBusy(false);}
 }
 const runDisease=()=>{if(!file){setError('Choose a leaf image first.');return;}const fd=new FormData();fd.append('image',file);request('/api/disease/classify',{method:'POST',body:fd});};
 const runSoil=()=>{
  const hasAnyValue=['nitrogen','phosphorus','potassium','ph'].some(k=>soil[k]!==''&&soil[k]!=null);
  if(soilMode!=='no_test'&&!hasAnyValue){setError('Enter at least one verified soil-test value, or choose “No soil test”.');return;}
  const payload={crop,location,soil_type:soil.soil_type,irrigation:soilIrrigation,
    nitrogen:soil.nitrogen===''?null:Number(soil.nitrogen),
    phosphorus:soil.phosphorus===''?null:Number(soil.phosphorus),
    potassium:soil.potassium===''?null:Number(soil.potassium),
    ph:soil.ph===''?null:Number(soil.ph)};
  request('/api/soil/advisory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
};
 const runSoilOCR=async()=>{if(!soilCardFile){setError('Choose a Soil Health Card image first.');return;}setOcrBusy(true);setError('');setOcrResult(null);try{const fd=new FormData();fd.append('image',soilCardFile);const r=await fetch(API+'/api/soil/ocr',{method:'POST',body:fd});const d=await r.json();if(!r.ok)throw new Error(d.detail||'OCR failed');setOcrResult(d);const v=d.extracted_values||{};setSoil(s=>({...s,nitrogen:v.nitrogen!=null?String(v.nitrogen):s.nitrogen,phosphorus:v.phosphorus!=null?String(v.phosphorus):s.phosphorus,potassium:v.potassium!=null?String(v.potassium):s.potassium,ph:v.ph!=null?String(v.ph):s.ph}));}catch(e){setError(e.message);}finally{setOcrBusy(false);}};
 const runWeather=()=>request('/api/weather/advisory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({city:location,crop,growth_stage:growth})});
 const runSatellite=()=>{
  let polygon=null;
  if(polygonText.trim()){
   try{polygon=JSON.parse(polygonText);}
   catch(e){setError('Field boundary is not valid JSON. Paste a valid GeoJSON Polygon.');return;}
   if(!['Polygon','MultiPolygon'].includes(polygon?.type)){setError('GeoJSON must have type Polygon or MultiPolygon.');return;}
  }
  request('/api/satellite/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
   latitude:Number(satelliteInput.latitude),longitude:Number(satelliteInput.longitude),
   radius_m:Number(satelliteInput.radius_m),start_date:satelliteInput.start_date,
   end_date:satelliteInput.end_date,max_cloud:Number(satelliteInput.max_cloud),
   polygon_geojson:polygon,crop,growth_stage:growth
  })});
 };
 const ask=async(e)=>{e.preventDefault();if(!question.trim())return;const q=question;setQuestion('');setHistory(h=>[...h,{role:'user',text:q}]);setBusy(true);setError('');try{const r=await fetch(API+'/api/assistant/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,crop,location,soil_context:`N ${soil.nitrogen}, P ${soil.phosphorus}, K ${soil.potassium}, pH ${soil.ph}`,weather_context:'Not fetched yet'})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Request failed');setHistory(h=>[...h,{role:'user',text:q},{role:'assistant',text:d.answer}]);}catch(err){setError(err.message);}finally{setBusy(false);}};

  async function loadMandiMarkets(){
    setMandiLoading(true);setMandiError('');setMandiResult(null);setNearestInfo(null);
    try{
      const origin = `${mandiForm.district}, ${mandiForm.state}`;
      const q=new URLSearchParams({location:origin,state:mandiForm.state,district:mandiForm.district});
      const r=await fetch(`${API}/api/mandi/nearest?${q}`);
      const d=await r.json();if(!r.ok)throw new Error(d.detail||'Could not find nearby mandis');
      const nearest=d.nearest_markets||[];
      if(!nearest.length)throw new Error('No mandi locations could be matched for the selected district and state. Check the selection and try again.');
      setNearestInfo(d);setMandiMarkets(nearest.map(x=>x.market));
      setMandiDistances(Object.fromEntries(nearest.map(x=>[x.market,String(x.distance_km)])));
    }catch(e){setMandiError(e.message);setMandiMarkets([]);setMandiDistances({});}
    finally{setMandiLoading(false);}
  }
  async function runSellingStrategy(){
    setMandiLoading(true);setMandiError('');setMandiResult(null);
    try{
      if(!mandiMarkets.length)throw new Error('Load mandi markets first.');
      const payload={
        ...mandiForm,
        quantity_quintals:Number(mandiForm.quantity_quintals),
        transport_rate_per_quintal_km:Number(mandiForm.transport_rate_per_quintal_km),
        handling_cost_per_quintal:Number(mandiForm.handling_cost_per_quintal),
        markets:mandiMarkets,
        market_distances_km:Object.fromEntries(Object.entries(mandiDistances).filter(([k,v])=>v!==''&&Number.isFinite(Number(v))).map(([k,v])=>[k,Number(v)]))
      };
      const r=await fetch(API+'/api/mandi/selling-strategy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const d=await r.json();if(!r.ok)throw new Error(d.detail||'Selling strategy request failed');
      setMandiResult(d);
    }catch(e){setMandiError(e.message);}
    finally{setMandiLoading(false);}
  }

  async function loadMandiPrices(){
    setMandiPricesLoading(true);setMandiPricesError('');setMandiPrices(null);
    try{
      const q=new URLSearchParams({state:mandiForm.state,district:mandiForm.district,commodity:mandiForm.commodity,variety:mandiForm.variety,limit:'25'});
      const r=await fetch(`${API}/api/mandi/prices?${q}`);const d=await r.json();
      if(!r.ok)throw new Error(d.detail||'Could not load mandi prices');
      setMandiPrices(d);
    }catch(e){setMandiPricesError(e.message);}finally{setMandiPricesLoading(false);}
  }
  async function runIntelligence(){
    setIntelligenceBusy(true);setIntelligenceError('');setIntelligenceResult(null);
    try{
      if(!locationConfirmed)throw new Error('Select your farm location from the suggestions first.');
      const optionalNumber=(v)=>v===''?null:Number(v);
      for(const key of ['nitrogen','phosphorus','potassium']){
        if(intelligenceForm[key]!==''&&(!Number.isFinite(Number(intelligenceForm[key]))||Number(intelligenceForm[key])<0))
          throw new Error(`${key} must be a valid non-negative number.`);
      }
      if(intelligenceForm.ph!==''&&(!Number.isFinite(Number(intelligenceForm.ph))||Number(intelligenceForm.ph)<0||Number(intelligenceForm.ph)>14))
        throw new Error('Soil pH must be between 0 and 14.');
      if(intelligenceForm.fetch_satellite){
        const lat=Number(intelligenceForm.latitude),lon=Number(intelligenceForm.longitude);
        if(!intelligenceForm.latitude||!intelligenceForm.longitude||!Number.isFinite(lat)||!Number.isFinite(lon)||lat < -90||lat > 90||lon < -180||lon > 180)
          throw new Error('Enter valid field coordinates for satellite analysis.');
      }
      const hasSoil=['nitrogen','phosphorus','potassium','ph'].some(k=>intelligenceForm[k]!=='');
      if(!intelligenceForm.fetch_weather&&!intelligenceForm.fetch_satellite&&!hasSoil)
        throw new Error('Add at least one soil reading or enable an evidence source.');
      const payload={
        crop,location,growth_stage:growth,soil_type:intelligenceForm.soil_type,
        nitrogen:optionalNumber(intelligenceForm.nitrogen),phosphorus:optionalNumber(intelligenceForm.phosphorus),
        potassium:optionalNumber(intelligenceForm.potassium),ph:optionalNumber(intelligenceForm.ph),
        fetch_weather:intelligenceForm.fetch_weather,fetch_satellite:intelligenceForm.fetch_satellite,
        latitude:intelligenceForm.fetch_satellite?Number(intelligenceForm.latitude):null,
        longitude:intelligenceForm.fetch_satellite?Number(intelligenceForm.longitude):null,
        radius_m:Number(intelligenceForm.radius_m),start_date:intelligenceForm.start_date,
        end_date:intelligenceForm.end_date,max_cloud:Number(intelligenceForm.max_cloud)
      };
      const r=await fetch(`${API}/api/intelligence/analyze`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const d=await r.json();if(!r.ok)throw new Error(d.detail||'Krishi Sahyog analysis failed');setIntelligenceResult(d);
    }catch(e){setIntelligenceError(e.message);}finally{setIntelligenceBusy(false);}
  }

 const title=nav.find(x=>x.id===page)?.label||'Overview';
 return <div className="app">
  <aside className={`sidebar ${mobile?'show':''}`}><div className="brand"><div className="brandmark"><Sprout size={23}/></div><div><b>KRISHI<span>SAHYOG</span></b><small>HARVEST INTELLIGENCE</small></div></div>
   <nav>{nav.map(n=><button key={n.id} className={page===n.id?'active':''} onClick={()=>{setPage(n.id);setMobile(false);reset();}}><n.icon size={18}/>{n.label}{page===n.id&&<span className="nav-dot"/>}</button>)}</nav>
   
  </aside>
  <main className="main"><header className="topbar"><button className="mobile-menu" onClick={()=>setMobile(!mobile)}><Menu/></button></header>
   <div className="content">
    {page==='overview' ? (
      <div className="overview-intro">
       <div><div className="eyebrow">YOUR AGRICULTURAL WORKSPACE</div><h1>Make better decisions, <em>from field to market.</em></h1><p>Practical crop insights, timely advisories and market intelligence in one place.</p></div>
       <div className="intro-mark"><Sprout size={23}/><span>KRISHI<br/>SAHYOG</span></div>
      </div>
    ) : <div className="page-head"><div><div className="eyebrow">AGRICULTURAL INTELLIGENCE</div><h1>{title}</h1><p>Get practical guidance using the information you provide.</p></div></div>}
   {error&&<div className="alert error"><AlertCircle size={18}/>{error}</div>}
   {page==='overview'&&<><div className="hero"><div className="hero-copy"><div className="hero-tag"><span/> YOUR FARM, BETTER INFORMED</div><h2>Make every field<br/>decision <em>count.</em></h2><p>Understand crop health, soil conditions and weather risks with AI-assisted agricultural guidance.</p><button onClick={()=>setPage('assistant')}>Ask the farmer assistant <ArrowUpRight size={17}/></button></div><div className="hero-art"><div className="sun-disc"/><div className="hill hill-back"/><div className="hill hill-front"/><div className="plant plant-one">♣</div><div className="plant plant-two">♣</div><div className="hero-stat"><span className="stat-icon"><Sprout size={17}/></span><div><b>Field-aware insights</b><small>Built around your crop context</small></div><CheckCircle2 size={17}/></div></div></div>
    <div className="section-row"><div><h3>Your advisory tools</h3><p>Choose a service to get started</p></div></div><div className="service-grid">{[{id:'disease',icon:Leaf,n:'Crop disease detection',d:'Upload a leaf photo to screen for possible disease.',tag:'IMAGE AI',color:'mint'},{id:'soil',icon:FlaskConical,n:'Soil health advisory',d:'Understand NPK and pH readings for your crop.',tag:'SOIL INSIGHTS',color:'sand'},{id:'weather',icon:CloudSun,n:'Weather advisory',d:'Review local weather and crop-specific precautions.',tag:'WEATHER',color:'blue'},{id:'satellite',icon:Satellite,n:'Satellite vegetation analysis',d:'Explore Sentinel-2 imagery with NDVI and EVI indices.',tag:'SENTINEL-2',color:'mint'},{id:'mandi',icon:Sprout,n:'Mandi prices & selling strategy',d:'Find nearby markets, inspect reported prices and compare estimated net realization.',tag:'LOCAL MARKET DATA',color:'sand'},{id:'intelligence',icon:BrainCircuit,n:'Krishi Sahyog Intelligence Core',d:'Combine verified soil, current weather and optional satellite observations into one field report.',tag:'FIELD INTELLIGENCE',color:'lav'},{id:'assistant',icon:MessageCircle,n:'AI farmer assistant',d:'Ask questions with your farm context included.',tag:'AI ASSISTANT',color:'lav'}].map(x=><button className="service-card" onClick={()=>{setPage(x.id);reset()}}><div className={`service-icon ${x.color}`}><x.icon size={21}/></div><span className="service-tag">{x.tag}</span><h4>{x.n}</h4><p>{x.d}</p><div className="card-link">Open tool <ArrowUpRight size={15}/></div></button>)}</div>
    <div className="note-strip"><div><CheckCircle2 size={18}/></div><p><b>Use local expertise for important decisions.</b> Krishi Sahyog provides preliminary AI-assisted information. Confirm disease treatment and fertilizer decisions with your local agriculture officer or KVK.</p></div></>}
   {page==='disease'&&<div className="work-grid"><div className="panel"><div className="panel-head"><div><span className="mini-label">IMAGE-BASED SCREENING</span><h3>Check a crop leaf</h3><p>Use a clear, close-up image with good lighting.</p></div><div className="round-icon mint"><Leaf/></div></div>{filePreview ? (
      <div className="leaf-preview">
       <img src={filePreview} alt="Selected crop leaf preview"/>
       <div className="leaf-preview-info">
        <b>{file?.name}</b>
        <span>{file?(file.size/1024/1024).toFixed(2)+' MB':''}</span>
        <label className="leaf-change-btn">Change image
         <input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{
          const selected=e.target.files?.[0];
          if(!selected)return;
          if(selected.size>8*1024*1024){setError('Image must be smaller than 8 MB.');e.target.value='';return;}
          setError('');setFile(selected);
         }}/>
        </label>
        <button type="button" onClick={()=>setFile(null)}>Remove image</button>
       </div>
      </div>
     ) : (
      <label className="upload-zone">
       <input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{
        const selected=e.target.files?.[0];
        if(!selected)return;
        if(selected.size>8*1024*1024){setError('Image must be smaller than 8 MB.');e.target.value='';return;}
        setError('');setFile(selected);
       }}/>
       <div className="upload-icon"><Upload/></div>
       <b>Drop a leaf image here</b>
       <span>or click to browse · JPG, PNG, WEBP · max 8 MB</span>
      </label>
     )}<button className="primary-btn" disabled={busy} onClick={runDisease}>{busy?<LoaderCircle className="spin"/>:<Leaf size={17}/>} Analyse leaf image</button><p className="fineprint">A model prediction is not a confirmed diagnosis. Image quality and supported disease classes affect results.</p></div><Result result={result} type="disease"/></div>}
   {page==='soil'&&<div className="work-grid"><div className="panel">
    <div className="panel-head"><div><span className="mini-label">SOIL HEALTH ASSESSMENT</span><h3>Tell us about your soil</h3><p>You can continue even if you don't have a Soil Health Card or laboratory report.</p></div><div className="round-icon sand"><FlaskConical/></div></div>
    <div className="soil-mode-grid" style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(150px,1fr))',gap:9,margin:'18px 0'}}>
     {[['card','I have a soil card'],['manual','I have test values'],['no_test','No soil test']].map(([value,label])=><button type="button" onClick={()=>{setSoilMode(value);setError('');setResult(null);}} style={{padding:'13px 10px',borderRadius:10,border:soilMode===value?'2px solid #557b5c':'1px solid #dce5dc',background:soilMode===value?'#edf5ec':'#fff',color:'#294b35',fontWeight:700,cursor:'pointer'}}>{label}</button>)}
    </div>
    {soilMode==='card'&&<>
     <label className="upload-zone"><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{setSoilCardFile(e.target.files?.[0]||null);setOcrResult(null);}}/><div className="upload-icon"><Upload/></div><b>{soilCardFile?soilCardFile.name:'Choose Soil Health Card image'}</b><span>JPG, PNG or WEBP · max 10 MB</span></label>
     <button className="primary-btn" disabled={ocrBusy||!soilCardFile} onClick={runSoilOCR}>{ocrBusy?<LoaderCircle className="spin"/>:<Upload size={17}/>} Extract soil values (OCR)</button>
     {ocrResult&&<div className="note-strip"><div><CheckCircle2 size={18}/></div><p><b>OCR extraction completed.</b> Review and correct the values below against the original report. OCR can misread digits and units.</p></div>}
    </>}
    {soilMode==='manual'&&<div className="note-strip"><div><AlertCircle size={18}/></div><p><b>Use values from a laboratory report.</b> Enter only the measurements you actually have. Leave unavailable values blank.</p></div>}
    {soilMode==='no_test'&&<div className="note-strip"><div><AlertCircle size={18}/></div><p><b>No report? That's okay.</b> Krishi Sahyog will give general crop and soil-management guidance. It will not guess your NPK or pH or calculate fertilizer doses.</p></div>}
    <div className="form-grid">
     {soilMode!=='no_test'&&[['nitrogen','Nitrogen (N)','Use report units'],['phosphorus','Phosphorus (P)','Use report units'],['potassium','Potassium (K)','Use report units'],['ph','Soil pH','0–14']].map(([k,l,u])=><label>{l}<input type="number" min={k==='ph'?0:0} max={k==='ph'?14:2000} step="any" placeholder="Enter verified value" value={soil[k]} onChange={e=>setSoil({...soil,[k]:e.target.value})}/><small>{u}</small></label>)}
     <label>Soil texture<select value={soil.soil_type} onChange={e=>setSoil({...soil,soil_type:e.target.value})}>{['Not specified','Sandy','Sandy loam','Loamy','Clay loam','Clay'].map(x=><option key={x}>{x}</option>)}</select></label>
     {soilMode==='no_test'&&<label>Irrigation<select value={soilIrrigation} onChange={e=>setSoilIrrigation(e.target.value)}>{['Rainfed','Canal','Borewell','Drip','Sprinkler','Other'].map(x=><option key={x}>{x}</option>)}</select></label>}
    </div>
    <button className="primary-btn" disabled={busy} onClick={runSoil}>{busy?<LoaderCircle className="spin"/>:<FlaskConical size={17}/>} {soilMode==='no_test'?'Generate preliminary advisory':'Generate soil advisory'}</button>
    <p className="fineprint">{soilMode==='no_test'?'This is general guidance, not a soil test. For nutrient-specific recommendations, collect a representative soil sample and get it tested through a soil-testing laboratory or KVK.':'Only use verified laboratory values. Confirm units and test methods before interpretation. Soil interpretation depends on local testing methods and crop requirements.'}</p>
    {ocrResult?.raw_text&&<details><summary>View raw OCR text</summary><pre style={{whiteSpace:'pre-wrap'}}>{ocrResult.raw_text}</pre></details>}
   </div><Result result={result} type="soil"/></div>}
   {page==='weather'&&<div className="work-grid"><div className="panel"><div className="panel-head"><div><span className="mini-label">LOCAL CONDITIONS</span><h3>Weather for your crop</h3><p>Enter your town, city or district to get local weather guidance.</p></div><div className="round-icon blue"><CloudSun/></div></div><label className="full-label">Location<input type="text" value={location} onChange={e=>setLocation(e.target.value)} placeholder="e.g. Bhopal, Madhya Pradesh" autoComplete="address-level2"/></label><label className="full-label">Crop growth stage<select value={growth} onChange={e=>setGrowth(e.target.value)}>{['Not specified','Sowing','Germination','Vegetative','Flowering','Fruiting / grain filling','Maturity','Harvest'].map(x=><option key={x}>{x}</option>)}</select></label><button className="primary-btn" disabled={busy||!location.trim()} onClick={runWeather}>{busy?<LoaderCircle className="spin"/>:<CloudSun size={17}/>} Get weather advisory</button><p className="fineprint">Enter a city, town or district name. Uses current weather conditions, not a detailed farm-level forecast or soil-moisture model.</p></div><Result result={result} type="weather"/></div>}
   {page==='satellite'&&<div className="work-grid"><div className="panel"><div className="panel-head"><div><span className="mini-label">SENTINEL-2 REMOTE SENSING</span><h3>Analyse field vegetation</h3><p>Use a field boundary for precise analysis, or leave it blank to use a circular test area.</p></div><div className="round-icon mint"><Satellite/></div></div><div className="form-grid"><label>Latitude<input type="number" step="any" value={satelliteInput.latitude} onChange={e=>setSatelliteInput({...satelliteInput,latitude:e.target.value})}/><small>Decimal degrees · −90 to 90</small></label><label>Longitude<input type="number" step="any" value={satelliteInput.longitude} onChange={e=>setSatelliteInput({...satelliteInput,longitude:e.target.value})}/><small>Decimal degrees · −180 to 180</small></label><label>Radius (metres)<input type="number" min="100" max="5000" value={satelliteInput.radius_m} onChange={e=>setSatelliteInput({...satelliteInput,radius_m:e.target.value})}/><small>Used only without polygon</small></label><label>Maximum scene cloud (%)<input type="number" min="0" max="100" value={satelliteInput.max_cloud} onChange={e=>setSatelliteInput({...satelliteInput,max_cloud:e.target.value})}/><small>Scene-level cloud filter</small></label><label>Start date<input type="date" value={satelliteInput.start_date} onChange={e=>setSatelliteInput({...satelliteInput,start_date:e.target.value})}/></label><label>End date<input type="date" value={satelliteInput.end_date} onChange={e=>setSatelliteInput({...satelliteInput,end_date:e.target.value})}/></label></div><label className="full-label" style={{display:'block',marginTop:'16px'}}>Field boundary GeoJSON (optional)<textarea rows={5} value={polygonText} onChange={e=>setPolygonText(e.target.value)} placeholder={'Paste a GeoJSON Polygon or MultiPolygon object. Example: {\"type\":\"Polygon\",\"coordinates\":[[[78.73,23.84],[78.74,23.84],[78.74,23.85],[78.73,23.85],[78.73,23.84]]]}'} style={{display:'block',width:'100%',marginTop:'7px',border:'1px solid #e5ebe2',borderRadius:'7px',background:'#fbfcfa',padding:'11px',color:'#26372b',font:'11px monospace',resize:'vertical'}}/><small style={{display:'block',marginTop:'6px',color:'#929d92'}}>Coordinates must be [longitude, latitude]. Polygon must be closed (first and last coordinate match). A supplied polygon takes priority over the circle.</small></label><label className="full-label" style={{display:'block',marginTop:'14px'}}>Crop growth stage<select value={growth} onChange={e=>setGrowth(e.target.value)} style={{display:'block',width:'100%',marginTop:'7px',border:'1px solid #e5ebe2',borderRadius:'7px',background:'#fbfcfa',padding:'11px',color:'#26372b'}}>{['Not specified','Sowing','Germination','Vegetative','Flowering','Fruiting / grain filling','Maturity','Harvest'].map(x=><option key={x}>{x}</option>)}</select></label><button className="primary-btn" disabled={busy} onClick={runSatellite}>{busy?<LoaderCircle className="spin"/>:<Satellite size={17}/>} Analyse satellite imagery</button><p className="fineprint">For accurate results, use your actual field boundary and crop stage. If no polygon is supplied, the API analyses a circular buffer around the coordinates. The time series compares monthly composites; it is not a crop-health diagnosis.</p></div><Result result={result} type="satellite"/></div>}

   {page==='mandi'&&<div className="work-grid">
    <div className="panel">
     <div className="panel-head"><div><span className="mini-label">LOCAL MARKET DATA COMPARISON</span><h3>Find the best mandi for your produce</h3><p>Compare reported market prices and estimate net realization after your transport and handling costs.</p></div><div className="round-icon mint"><Sprout/></div></div>
     <div className="form-grid">
      <label>State<select value={mandiForm.state} disabled={mandiFiltersLoading||!mandiFilters.states.length} onChange={e=>{const next=e.target.value;const firstDistrict=mandiFilters.districts.find(x=>x.state_id===mandiFilters.states.find(s=>s.name===next)?.id);setMandiForm({...mandiForm,state:next,district:firstDistrict?.name||'',variety:''});setMandiMarkets([]);setMandiDistances({});setMandiResult(null);}}>{mandiFilters.states.map(x=><option key={x.id} value={x.name}>{x.name}</option>)}</select></label>
      <label>District<select value={mandiForm.district} onChange={e=>{setMandiForm({...mandiForm,district:e.target.value});setMandiMarkets([]);setMandiDistances({});setMandiResult(null);}}><option value="">All districts</option>{availableDistricts.map(x=><option key={x.id} value={x.name}>{x.name}</option>)}</select></label>
      <label>Commodity<select value={mandiForm.commodity} onChange={e=>{setMandiForm({...mandiForm,commodity:e.target.value,variety:''});setMandiMarkets([]);setMandiDistances({});setMandiResult(null);}}>{mandiFilters.commodities.map(x=><option key={x.id} value={x.name}>{x.name}</option>)}</select></label>
      <label>Variety (optional)<select value={mandiForm.variety} onChange={e=>{setMandiForm({...mandiForm,variety:e.target.value});setMandiMarkets([]);setMandiResult(null);}}><option value="">All reported varieties</option>{availableVarieties.map(x=><option key={`${x.id}-${x.name}`} value={x.name}>{x.name}</option>)}</select></label>
      <label>Quantity (quintals)<input type="number" min="0.01" step="any" value={mandiForm.quantity_quintals} onChange={e=>setMandiForm({...mandiForm,quantity_quintals:e.target.value})}/></label>
      <label>Transport rate (₹ / quintal / km)<input type="number" min="0" step="any" value={mandiForm.transport_rate_per_quintal_km} onChange={e=>setMandiForm({...mandiForm,transport_rate_per_quintal_km:e.target.value})}/></label>
      <label>Handling cost (₹ / quintal)<input type="number" min="0" step="any" value={mandiForm.handling_cost_per_quintal} onChange={e=>setMandiForm({...mandiForm,handling_cost_per_quintal:e.target.value})}/></label>
     </div>
     {mandiFiltersLoading&&<p className="fineprint">Loading states, districts and commodities from the local Agriculture Marketing dataset…</p>}
     <p className="fineprint">Search origin: {mandiForm.district ? `${mandiForm.district}, ${mandiForm.state}` : 'Select a district above'}.</p>
     <button className="primary-btn" disabled={mandiLoading||mandiFiltersLoading||!mandiFilters.states.length||!mandiForm.district} onClick={loadMandiMarkets}>{mandiLoading?<LoaderCircle className="spin"/>:<MapPin size={17}/>} Find 3 nearest mandis</button>
     {mandiPricesError&&<div className="alert error" style={{marginTop:10}}><AlertCircle size={17}/>{mandiPricesError}</div>}
     {mandiPrices&&<div style={{marginTop:16}}><h4>Reported mandi prices</h4><p className="fineprint">{mandiPrices.reported_record_count??0} reported price records · Latest date: {mandiPrices.latest_arrival_date||'Not available'} · Source: local Agriculture Marketing dataset</p>{mandiPrices.records?.filter(x=>x.reported).slice(0,12).length?<div style={{overflowX:'auto'}}><table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}><thead><tr><th align="left">Market</th><th align="left">Variety</th><th align="right">Date</th><th align="right">Modal price</th></tr></thead><tbody>{mandiPrices.records.filter(x=>x.reported).slice(0,12).map((x,i)=><tr key={`${x.market}-${x.date}-${i}`}><td>{x.market}</td><td>{x.variety}</td><td align="right">{x.date}</td><td align="right">₹{Number(x.modal_price).toLocaleString('en-IN')} {x.price_unit||''}</td></tr>)}</tbody></table></div>:<p className="fineprint">The local dataset has no reported prices for this selection.</p>}</div>}
     {mandiMarkets.length>0&&<><div style={{marginTop:22}}><span className="mini-label">THREE NEAREST MATCHED MANDIS</span><h3>Nearby markets</h3><p className="fineprint">Distances are automatically estimated from map locations as straight-line distances, not road distances. Verify before dispatch.</p>
      <div style={{display:'grid',gap:10,marginTop:12}}>{mandiMarkets.map((name,i)=><div key={name} style={{display:'flex',justifyContent:'space-between',gap:12,padding:'12px',border:'1px solid #e5ebe2',borderRadius:10}}><b>{i+1}. {name}</b><span>{nearestInfo?.nearest_markets?.[i]?.distance_km} km</span></div>)}</div>
     </div><button className="primary-btn" disabled={mandiLoading} onClick={runSellingStrategy}>{mandiLoading?<LoaderCircle className="spin"/>:<ArrowUpRight size={17}/>} Compare prices and net realization</button></>}
     {mandiError&&<div className="alert error" style={{marginTop:12}}><AlertCircle size={17}/>{mandiError}</div>}
     <p className="fineprint">Source: local Agriculture Marketing dataset. Prices are historical reported observations, not guaranteed offers. Net values are estimates based on your entered costs and distances.</p>
    </div>
    <div className="result-panel">
     <span className="mini-label">SELLING DECISION SUPPORT</span><h3>Market comparison</h3>
     {!mandiResult?<><div className="empty-art"><Sprout size={30}/></div><p>Find your three nearest mandis, then compare reported prices and estimated net realization.</p></>:mandiResult.status==='no_price_data'?<div className="result-text">{mandiResult.message}</div>:<>
      <div className="weather-cards">
       <div><small>Markets checked</small><b>{mandiResult.markets_checked}</b></div>
       <div><small>Markets with prices</small><b>{mandiResult.markets_with_reported_prices}</b></div>
       <div><small>Markets with distance</small><b>{mandiResult.markets_with_distance}</b></div>
      </div>
      <div className="condition">Latest reported price date: {mandiResult.latest_arrival_date||'Not available'} · Data freshness: {mandiResult.data_freshness||'unknown'}</div>
      {mandiResult.best_estimated_net_market&&<div className="prediction"><span>BEST ESTIMATED NET REALIZATION</span><b>{mandiResult.best_estimated_net_market.market}</b><small>₹{Number(mandiResult.best_estimated_net_market.net_price_per_quintal).toLocaleString('en-IN',{maximumFractionDigits:2})} / quintal · Estimated total ₹{Number(mandiResult.best_estimated_net_market.estimated_net_value).toLocaleString('en-IN',{maximumFractionDigits:2})}</small></div>}
      <h4 style={{marginTop:18}}>Net realization ranking</h4>
      {mandiResult.net_realization_ranking?.length?<div style={{overflowX:'auto'}}><table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}><thead><tr><th align="left">Market</th><th align="right">Gross ₹/q</th><th align="right">Distance</th><th align="right">Net ₹/q</th></tr></thead><tbody>{mandiResult.net_realization_ranking.map(x=><tr key={x.market}><td>{x.market}<small style={{display:'block',color:'#839083'}}>{x.variety} · {x.price_date}</small></td><td align="right">{Number(x.gross_price_per_quintal).toLocaleString('en-IN')}</td><td align="right">{x.distance_km_one_way} km</td><td align="right"><b>{Number(x.net_price_per_quintal).toLocaleString('en-IN')}</b></td></tr>)}</tbody></table></div>:<p className="fineprint">No market has both a reported price and a supplied distance. Enter distances to calculate net realization.</p>}
      <h4 style={{marginTop:18}}>Highest reported gross prices</h4>
      {mandiResult.gross_price_ranking?.slice(0,8).map(x=><div className="alt-list" key={x.market}><div>{x.market} · {x.variety}<span>₹{Number(x.gross_price_per_quintal).toLocaleString('en-IN')} / q</span></div></div>)}
      <p className="fineprint">{mandiResult.disclaimer}</p>
     </>}
    </div>
   </div>}


   {page==='intelligence'&&<div className="work-grid intelligence-grid">
    <div className="panel intelligence-form">
     <div className="panel-head"><div><span className="mini-label">FIELD ASSESSMENT</span><h3>Build your field intelligence report</h3><p>Combine crop context, verified soil readings and available field observations.</p></div><div className="round-icon mint"><BrainCircuit/></div></div>
     <div className="location-field">
      <label htmlFor="ks-location">Farm location</label>
      <div className="location-input-wrap"><MapPin size={18}/><input id="ks-location" type="text" value={location} placeholder="Search village, town or district" autoComplete="off" onChange={e=>{setLocation(e.target.value);setLocationConfirmed(false);setLocationSuggestions([]);setIntelligenceResult(null);}}/>{locationSearching&&<LoaderCircle className="spin" size={17}/>}</div>
      {locationSuggestions.length>0&&<div className="location-suggestions">{locationSuggestions.map((place,i)=>{const p=place.properties||{};const coords=place.geometry?.coordinates||[];const label=[p.name,p.city||p.district,p.state,p.country].filter(Boolean).filter((v,j,a)=>a.indexOf(v)===j).join(', ');return <button type="button" key={`${label}-${i}`} onClick={()=>{setLocation(label);setLocationConfirmed(true);setLocationSuggestions([]);if(coords.length>=2)setIntelligenceForm(old=>({...old,latitude:String(coords[1]),longitude:String(coords[0])}));}}><MapPin size={16}/><span>{label}</span></button>;})}</div>}
      <small>{locationConfirmed?'Location selected. Verify the field coordinates before satellite analysis.':'Choose a suggested place to confirm the location.'}</small>
     </div>
     <div className="form-grid intelligence-context-grid">
      <label htmlFor="ks-crop">Primary crop<select id="ks-crop" value={crop} onChange={e=>setCrop(e.target.value)}>{['Wheat','Rice','Soybean','Maize','Cotton','Chickpea','Tomato','Potato'].map(x=><option key={x}>{x}</option>)}</select></label>
      <label htmlFor="ks-growth">Growth stage<select id="ks-growth" value={growth} onChange={e=>setGrowth(e.target.value)}>{['Not specified','Sowing','Germination','Seedling','Vegetative','Flowering','Fruiting','Maturity','Harvest'].map(x=><option key={x}>{x}</option>)}</select></label>
     </div>
     <div className="section-divider"><span>SOIL INFORMATION</span><small>Enter values from a verified soil report</small></div>
     <div className="form-grid intelligence-context-grid">
      <label htmlFor="ks-soil">Soil type<select id="ks-soil" value={intelligenceForm.soil_type} onChange={e=>setIntelligenceForm({...intelligenceForm,soil_type:e.target.value})}>{['Not specified','Sandy','Sandy loam','Loamy','Clay loam','Clay'].map(x=><option key={x}>{x}</option>)}</select></label>
      <label htmlFor="ks-ph">Soil pH<input id="ks-ph" type="number" min="0" max="14" step="0.1" inputMode="decimal" placeholder="0–14" value={intelligenceForm.ph} onChange={e=>setIntelligenceForm({...intelligenceForm,ph:e.target.value})}/></label>
     </div>
     <div className="npk-grid">
      <label htmlFor="ks-n">Nitrogen<input id="ks-n" type="number" min="0" step="any" inputMode="decimal" placeholder="Optional" value={intelligenceForm.nitrogen} onChange={e=>setIntelligenceForm({...intelligenceForm,nitrogen:e.target.value})}/></label>
      <label htmlFor="ks-p">Phosphorus<input id="ks-p" type="number" min="0" step="any" inputMode="decimal" placeholder="Optional" value={intelligenceForm.phosphorus} onChange={e=>setIntelligenceForm({...intelligenceForm,phosphorus:e.target.value})}/></label>
      <label htmlFor="ks-k">Potassium<input id="ks-k" type="number" min="0" step="any" inputMode="decimal" placeholder="Optional" value={intelligenceForm.potassium} onChange={e=>setIntelligenceForm({...intelligenceForm,potassium:e.target.value})}/></label>
     </div>
     <p className="fineprint readable-note">Enter NPK values only when their units and reporting method are known. Do not mix kg/ha, ppm or qualitative ratings. The current API does not interpret NPK units.</p>
     <div className="section-divider"><span>ADDITIONAL FIELD EVIDENCE</span><small>Optional analysis modules</small></div>
     <div className="intelligence-options">
      <label className="option-row"><input type="checkbox" checked={intelligenceForm.fetch_weather} disabled={!locationConfirmed} onChange={e=>setIntelligenceForm({...intelligenceForm,fetch_weather:e.target.checked})}/><span><b>Current weather</b><small>Retrieve weather conditions for the selected location.</small></span></label>
      <label className="option-row"><input type="checkbox" checked={intelligenceForm.fetch_satellite} disabled={!locationConfirmed} onChange={e=>setIntelligenceForm({...intelligenceForm,fetch_satellite:e.target.checked})}/><span><b>Satellite NDVI / EVI</b><small>Analyse vegetation indices around your field coordinates.</small></span></label>
     </div>
     {intelligenceForm.fetch_satellite&&<div className="satellite-location-box"><b>Field analysis area</b><p>Village coordinates may not represent your actual farm. Verify them before analysis.</p><div className="form-grid">
      <label htmlFor="ks-lat">Latitude<input id="ks-lat" type="number" step="any" value={intelligenceForm.latitude} onChange={e=>setIntelligenceForm({...intelligenceForm,latitude:e.target.value})}/></label>
      <label htmlFor="ks-lon">Longitude<input id="ks-lon" type="number" step="any" value={intelligenceForm.longitude} onChange={e=>setIntelligenceForm({...intelligenceForm,longitude:e.target.value})}/></label>
      <label htmlFor="ks-radius">Radius (metres)<input id="ks-radius" type="number" min="100" max="5000" value={intelligenceForm.radius_m} onChange={e=>setIntelligenceForm({...intelligenceForm,radius_m:e.target.value})}/></label>
      <label htmlFor="ks-cloud">Maximum cloud (%)<input id="ks-cloud" type="number" min="0" max="100" value={intelligenceForm.max_cloud} onChange={e=>setIntelligenceForm({...intelligenceForm,max_cloud:e.target.value})}/></label>
      <label htmlFor="ks-start">Start date<input id="ks-start" type="date" value={intelligenceForm.start_date} onChange={e=>setIntelligenceForm({...intelligenceForm,start_date:e.target.value})}/></label>
      <label htmlFor="ks-end">End date<input id="ks-end" type="date" value={intelligenceForm.end_date} onChange={e=>setIntelligenceForm({...intelligenceForm,end_date:e.target.value})}/></label>
     </div><p className="fineprint readable-note">This uses a circular area around the coordinates, not an exact farm boundary. Use the Satellite Imagery page for a polygon.</p></div>}
     <div className="evidence-summary"><span>Evidence selected</span><div className="evidence-chips">
      <span className={['nitrogen','phosphorus','potassium','ph'].some(k=>intelligenceForm[k]!=='')?'available':''}>Soil {['nitrogen','phosphorus','potassium','ph'].some(k=>intelligenceForm[k]!=='')?'✓':'—'}</span>
      <span className={intelligenceForm.fetch_weather?'available':''}>Weather {intelligenceForm.fetch_weather?'✓':'—'}</span>
      <span className={intelligenceForm.fetch_satellite?'available':''}>Satellite {intelligenceForm.fetch_satellite?'✓':'—'}</span>
     </div></div>
     <button className="primary-btn" disabled={intelligenceBusy||!locationConfirmed||!(intelligenceForm.fetch_weather||intelligenceForm.fetch_satellite||['nitrogen','phosphorus','potassium','ph'].some(k=>intelligenceForm[k]!==''))} onClick={runIntelligence}>{intelligenceBusy?<><LoaderCircle className="spin"/> Analysing field evidence…</>:<><BrainCircuit size={17}/> Run Krishi Sahyog Intelligence Analysis</>}</button>
     {!locationConfirmed&&<p className="form-hint">Select a farm location before running the analysis.</p>}
     {intelligenceError&&<div className="alert error" style={{marginTop:12}}><AlertCircle size={17}/>{intelligenceError}</div>}
     <p className="fineprint readable-note">Krishi Sahyog uses supplied measurements and retrieved observations. Missing data is not inferred. This report does not prescribe fertilizer doses or replace local agronomic advice.</p>
    </div>
    <div className="result-panel intelligence-output">
     <span className="mini-label">FIELD INTELLIGENCE OUTPUT</span><h3>Krishi Sahyog field analysis</h3>
     {intelligenceBusy?<div className="analysis-loading"><LoaderCircle className="spin" size={28}/><h4>Analysing your field</h4><p>Retrieving available evidence and preparing the report.</p><div className="loading-line"/><div className="loading-line"/><div className="loading-line short"/></div>:!intelligenceResult?<div className="intelligence-empty"><div className="empty-art"><BrainCircuit size={30}/></div><h3>Your field report will appear here</h3><p>Krishi Sahyog combines the evidence you provide into a structured agricultural intelligence report.</p><div className="report-preview"><div><CheckCircle2 size={16}/> Field overview</div><div><CheckCircle2 size={16}/> Soil observations</div><div><CheckCircle2 size={16}/> Weather observations</div><div><CheckCircle2 size={16}/> Satellite observations</div><div><CheckCircle2 size={16}/> Risks and next checks</div></div><p className="fineprint">Sections appear only when corresponding evidence is available.</p></div>:<>
      <div className="condition">{intelligenceResult.crop} · {intelligenceResult.location} · {intelligenceResult.growth_stage} · AI: {intelligenceResult.ai_status}</div>
      <div className="evidence-summary"><span>Sources returned</span><div className="evidence-chips"><span className={intelligenceResult.weather?'available':''}>Weather {intelligenceResult.weather?'✓':'—'}</span><span className={intelligenceResult.satellite?'available':''}>Satellite {intelligenceResult.satellite?'✓':'—'}</span><span className="available">Submitted soil inputs ✓</span></div></div>
      {intelligenceResult.module_errors?.length>0&&<div className="partial-warning"><AlertCircle size={17}/><div><b>Some sources were unavailable</b>{intelligenceResult.module_errors.map((x,i)=><p key={i}>{x.module}: {x.error}</p>)}<small>The report was generated using remaining available evidence.</small></div></div>}
      <div className="report-section"><h4>Field intelligence findings</h4><MarkdownReport text={intelligenceResult.intelligence_report} /></div>
      {intelligenceResult.rule_engine&&<div className="report-section"><h4>Deterministic observations</h4>{intelligenceResult.rule_engine.observations?.length?intelligenceResult.rule_engine.observations.map((x,i)=><div className="alt-list" key={i}><div>{x}</div></div>):<p>No deterministic observations were returned.</p>}{intelligenceResult.rule_engine.warnings?.length>0&&<><h4>Warnings</h4>{intelligenceResult.rule_engine.warnings.map((x,i)=><p className="report-warning" key={i}>{x}</p>)}</>}</div>}
      {intelligenceResult.weather&&<div className="report-section"><h4>Weather evidence</h4><div className="condition">{intelligenceResult.weather.conditions||'Conditions unavailable'} · {intelligenceResult.weather.temperature_c??'—'}°C · Humidity {intelligenceResult.weather.humidity_percent??'—'}%</div></div>}
      {intelligenceResult.satellite&&<div className="report-section"><h4>Satellite evidence</h4>{intelligenceResult.satellite.indices&&<div className="weather-cards"><div><small>NDVI</small><b>{intelligenceResult.satellite.indices.ndvi_mean??'—'}</b></div><div><small>EVI</small><b>{intelligenceResult.satellite.indices.evi_mean??'—'}</b></div><div><small>Images</small><b>{intelligenceResult.satellite.image_count??'—'}</b></div></div>}</div>}
      <p className="fineprint readable-note">{intelligenceResult.fallback_used?'AI text generation used a fallback. Review deterministic observations.':'Generated from available inputs and retrieved data. Verify important agronomic decisions locally.'}</p>
     </>}
    </div>
   </div>}

   {page==='assistant'&&<div className="chat-layout"><div className="chat-panel"><div className="chat-head"><div className="round-icon mint"><MessageCircle/></div><div><b> Farmer Assistant</b><small><i/> AI assistant · context-aware</small></div><span className="powered">GEMINI</span></div><div className="messages">{history.length===0&&<div className="welcome"><div className="welcome-icon"><Sprout size={25}/></div><h3>How can I help your farm today?</h3><p>Ask about crop care, soil readings, pests, or weather-related precautions.</p><div className="suggestions">{['How should I care for wheat at this stage?','What does my soil pH indicate?','What should I check before irrigation?'].map(q=><button onClick={()=>setQuestion(q)}>{q}<ArrowUpRight size={14}/></button>)}</div></div>}{history.map((m,i)=><div className={`bubble ${m.role}`}>{m.text}</div>)}{busy&&<div className="bubble assistant"><LoaderCircle className="spin" size={16}/> Thinking…</div>}</div><form className="chat-input" onSubmit={ask}><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask an agricultural question…"/><button disabled={busy||!question.trim()}><Send size={17}/></button></form><div className="chat-disclaimer">AI-generated information can be wrong. Verify high-impact decisions with a qualified local expert.</div></div><div className="side-context"><span className="mini-label">ACTIVE CONTEXT</span><h4>Your farm details</h4><div><small>LOCATION</small><b>{location}</b></div><div><small>PRIMARY CROP</small><b>{crop}</b></div><div><small>SOIL INPUTS</small><b>N {soil.nitrogen} · P {soil.phosphorus} · K {soil.potassium} · pH {soil.ph}</b></div><p>These details are sent with your question to make the response more relevant.</p></div></div>}
   <footer>Krishi Sahyog <span>·</span> Agricultural decision support prototype <span>·</span> Not a substitute for official agronomic advice</footer>
   </div></main>
 </div>
}
function Result({result,type}){
 if(!result)return <div className="result-empty"><div className="empty-art"><Sprout size={30}/></div><h3>Your results will appear here</h3><p>Complete the form and run the analysis to see your advisory.</p><div className="empty-points"><span><CheckCircle2 size={15}/> Clear inputs</span><span><CheckCircle2 size={15}/> Context-aware output</span><span><CheckCircle2 size={15}/> Source transparency</span></div></div>;
 return <div className="result-panel"><span className="mini-label">ANALYSIS RESULT</span><h3>{type==='disease'?'Leaf screening result':type==='soil'?'Soil health advisory':type==='satellite'?'Satellite vegetation analysis':'Weather & crop advisory'}</h3>{type==='disease'?<><div className="prediction"><span>TOP PREDICTION</span><b>{result.prediction}</b><small>Model confidence: {(result.confidence*100).toFixed(1)}%</small></div>{result.alternatives?.length>0&&<div className="alt-list"><b>Other model predictions</b>{result.alternatives.map(a=><div>{a.label}<span>{(a.confidence*100).toFixed(1)}%</span></div>)}</div>}<p className="disclaimer">{result.disclaimer}</p></>:type==='soil'?<><div className="result-text">
  <AdvisoryText text={result.advisory} />
</div><p className="source-note">Source: {result.source}</p></>:type==='satellite'?<><div className="weather-cards">{[['Mean NDVI',result.indices?.ndvi_mean,'',Leaf],['Mean EVI',result.indices?.evi_mean,'',Satellite],['Images found',result.image_count,'',CloudSun]].map(([l,v,u,I])=><div><I size={17}/><small>{l}</small><b>{v??'—'}{u}</b></div>)}</div><div className="condition">Latest image: {result.latest_image_date||'Not available'} · {result.source}</div><div className="source-note">Area: {result.area?.mode==='polygon'?'Field boundary polygon':'Circular buffer'} · Crop: {result.crop_context?.crop||crop} · Stage: {result.crop_context?.growth_stage||growth}</div><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:'14px',marginTop:'16px'}}>{[['NDVI',result.previews?.ndvi],['EVI',result.previews?.evi]].map(([label,url])=><div><b style={{display:'block',marginBottom:'8px'}}>{label} preview</b>{url?<a href={url} target="_blank" rel="noreferrer"><img src={url} alt={`${label} satellite index preview`} style={{width:'100%',display:'block',borderRadius:'12px',border:'1px solid #dce5df'}}/></a>:<p>Preview unavailable</p>}</div>)}</div><div style={{marginTop:'18px'}}><b style={{fontSize:'13px'}}>Monthly vegetation trend</b><p className="fineprint">Each point is the mean index from that month's median Sentinel-2 composite over the selected area.</p>{result.timeseries?.length? <div style={{overflowX:'auto',marginTop:'10px'}}><table style={{width:'100%',borderCollapse:'collapse',fontSize:'10px'}}><thead><tr style={{textAlign:'left',color:'#819083',borderBottom:'1px solid #e8eee6'}}><th style={{padding:'9px 6px'}}>Month</th><th style={{padding:'9px 6px'}}>NDVI</th><th style={{padding:'9px 6px'}}>EVI</th><th style={{padding:'9px 6px'}}>Images</th></tr></thead><tbody>{result.timeseries.map(row=><tr key={row.month} style={{borderBottom:'1px solid #edf1eb'}}><td style={{padding:'9px 6px',color:'#526354'}}>{row.month}</td><td style={{padding:'9px 6px',fontWeight:700,color:'#47754b'}}>{row.ndvi_mean.toFixed(4)}</td><td style={{padding:'9px 6px',fontWeight:700,color:'#668c69'}}>{row.evi_mean.toFixed(4)}</td><td style={{padding:'9px 6px',color:'#7f8d80'}}>{row.image_count}</td></tr>)}</tbody></table></div>:<p className="fineprint">No monthly observations with valid pixels were available in this date range.</p>}</div><p className="fineprint">{result.crop_context?.note||'Vegetation indices are not a confirmed crop-health diagnosis. Compare trends with crop type, growth stage and field observations.'}</p><p className="source-note">Dataset: {result.collection} · {result.date_range?.start} to {result.date_range?.end}</p></>:<><div className="weather-cards">{[['Temperature',result.weather?.temperature_c,'°C',Sun],['Humidity',result.weather?.humidity_percent,'%',Droplets],['Wind',result.weather?.wind_speed_m_s,'m/s',Wind]].map(([l,v,u,I])=><div><I size={17}/><small>{l}</small><b>{v??'—'}{u}</b></div>)}</div><div className="condition">{result.weather?.city}: {result.weather?.conditions}</div><div className="result-text">
  <AdvisoryText text={result.advisory} />
</div></>}<div className="result-foot"><CheckCircle2 size={15}/> Generated for your submitted context</div></div>
}
export default App;

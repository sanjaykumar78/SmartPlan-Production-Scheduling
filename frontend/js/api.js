const API_BASE_URL='https://smartplan-production-scheduling-production.up.railway.app/api';
const MockStore={orders:[...SmartPlanData.orders],machines:[...SmartPlanData.machines],disruptions:[],schedule:SmartPlanData.orders.map((order,index)=>({order_id:order.id,machine_id:order.machine,product_name:order.product,start_time:`2026-09-18T${String(8+index%8).padStart(2,'0')}:00:00`,end_time:`2026-09-18T${String(9+index%8).padStart(2,'0')}:30:00`,duration:order.processingTime,status:order.status,delay_minutes:order.status==='Delayed'?45:0})),reports:{production:SmartPlanData.production}};
const apiState={usingFallback:false,lastError:null};

async function requestApi(path,options={}){
  const response=await fetch(`${API_BASE_URL}${path}`,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(payload.message||`Request failed (${response.status})`);
  return payload.data===undefined?payload:payload.data;
}

function useFallback(error){apiState.usingFallback=true;apiState.lastError=error;return true}
function normalizeOrder(order){return {...order,backendId:order.id,id:order.orderNumber||order.id,product:order.productName||order.product,machine:order.machine||'Unassigned',processingTime:order.processingTime||order.processing_time||0}}
function normalizeMachine(machine){return {...machine,backendId:machine.id,id:machine.machineId||machine.id,name:machine.machineName||machine.name,type:machine.machineType||machine.type,availableFrom:machine.availableFrom||'Now',currentOrder:machine.currentOrder||'-'}}
function normalizeReport(report){if(!report)return report;report.production=report.dailySchedule?.map(item=>item.entries)||report.production||SmartPlanData.production;return report}
function fallbackOrders(){apiState.usingFallback=true;return MockStore.orders.map(normalizeOrder)}
function fallbackMachines(){apiState.usingFallback=true;return MockStore.machines.map(normalizeMachine)}

const api={
  async fetchOrders(){try{const data=await requestApi('/orders');return data.map(normalizeOrder)}catch(error){useFallback(error);return fallbackOrders()}},
  async createOrder(order){try{return await requestApi('/orders',{method:'POST',body:JSON.stringify({id:order.id,product:order.product,quantity:order.quantity,processingTime:order.processingTime,priority:order.priority,deadline:order.deadline,requiredMachineType:order.requiredMachineType||'CNC',status:order.status||'Pending',notes:order.notes})})}catch(error){useFallback(error);MockStore.orders.unshift(order);return order}},
  async updateOrder(id,changes){const backendId=SmartPlanData.orders.find(order=>order.id===id)?.backendId||id;try{return await requestApi(`/orders/${backendId}`,{method:'PUT',body:JSON.stringify(changes)})}catch(error){useFallback(error);const item=MockStore.orders.find(order=>order.id===id);if(item)Object.assign(item,changes);return item}},
  async deleteOrder(id){const backendId=SmartPlanData.orders.find(order=>order.id===id)?.backendId||id;try{await requestApi(`/orders/${backendId}`,{method:'DELETE'});return true}catch(error){useFallback(error);MockStore.orders=MockStore.orders.filter(order=>order.id!==id);return true}},
  async fetchMachines(){try{const data=await requestApi('/machines');return data.map(normalizeMachine)}catch(error){useFallback(error);return fallbackMachines()}},
  async createMachine(machine){try{return await requestApi('/machines',{method:'POST',body:JSON.stringify(machine)})}catch(error){useFallback(error);MockStore.machines.push(machine);return machine}},
  async updateMachine(id,changes){try{return await requestApi(`/machines/${id}`,{method:'PUT',body:JSON.stringify(changes)})}catch(error){useFallback(error);return changes}},
  async deleteMachine(id){try{await requestApi(`/machines/${id}`,{method:'DELETE'});return true}catch(error){useFallback(error);return true}},
  async fetchSchedule(){try{return await requestApi('/schedule')}catch(error){useFallback(error);return MockStore.schedule}},
  async generateSchedule(){try{return await requestApi('/schedule/generate',{method:'POST',body:'{}'})}catch(error){useFallback(error);return this.fetchSchedule()}},
  async reschedule(){try{return await requestApi('/schedule/reschedule',{method:'POST',body:'{}'})}catch(error){useFallback(error);return this.fetchSchedule()}},
  async fetchDisruptions(){try{return await requestApi('/disruptions')}catch(error){useFallback(error);return MockStore.disruptions}},
  async createDisruption(item){try{return await requestApi('/disruptions',{method:'POST',body:JSON.stringify(item)})}catch(error){useFallback(error);MockStore.disruptions.unshift(item);return item}},
  async fetchReports(){try{return await requestApi('/reports')}catch(error){useFallback(error);return MockStore.reports}},
  async fetchNotifications(){return [...SmartPlanData.notifications]}
};

async function loadPageData(page){
  apiState.usingFallback=false;apiState.lastError=null;
  if(page==='dashboard'){[SmartPlanData.orders,SmartPlanData.machines,SmartPlanData.reports]=await Promise.all([api.fetchOrders(),api.fetchMachines(),api.fetchReports()]);SmartPlanData.reports=normalizeReport(SmartPlanData.reports);SmartPlanData.production=SmartPlanData.reports.production}
  if(page==='orders')SmartPlanData.orders=await api.fetchOrders();
  if(page==='machines')SmartPlanData.machines=await api.fetchMachines();
  if(page==='schedule'){SmartPlanData.schedule=await api.fetchSchedule();SmartPlanData.orders=SmartPlanData.schedule.map(job=>({id:job.order_id,product:job.product_name||job.product||`Order ${job.order_id}`,processingTime:job.duration||0,machine:job.machine_id,status:job.status,priority:'Medium'}))}
  if(page==='disruptions')SmartPlanData.disruptions=await api.fetchDisruptions();
  if(page==='reports'){SmartPlanData.reports=normalizeReport(await api.fetchReports());SmartPlanData.production=SmartPlanData.reports.production}
  return apiState;
}

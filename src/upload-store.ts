export type UploadRecord={id:string;name:string;size:number;addedAt:string;company:string;sourceUrl:string;pages:{page:number;text:string}[];ocrPages:number[];bytes:ArrayBuffer};
async function db() {
 return new Promise<IDBDatabase>((resolve,reject)=>{
  const req=indexedDB.open('disclosure-reference-documents',1);
  req.onupgradeneeded=()=>req.result.createObjectStore('documents',{keyPath:'id'});
  req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
 });
}
async function transact<T>(mode:IDBTransactionMode,op:(store:IDBObjectStore)=>IDBRequest<T>):Promise<T>{
 const d=await db();return new Promise((resolve,reject)=>{const tx=d.transaction('documents',mode);const req=op(tx.objectStore('documents'));let result:T;req.onsuccess=()=>{result=req.result;};tx.oncomplete=()=>{d.close();resolve(result);};tx.onerror=tx.onabort=()=>{d.close();reject(tx.error||req.error);};});
}
export const allUploads=()=>transact('readonly',s=>s.getAll()) as Promise<UploadRecord[]>;
export const saveUpload=(r:UploadRecord)=>transact('readwrite',s=>s.put(r));
export const deleteUpload=(id:string)=>transact('readwrite',s=>s.delete(id));

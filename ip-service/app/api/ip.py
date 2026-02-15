from fastapi import APIRouter, HTTPException
from app.api.models import GeoOut
import maxminddb
        
ip = APIRouter()

@ip.get('/{ip}/')
async def get_geo(ip: str):
    
    error = None
    out = GeoOut()
    if not ip:
        raise HTTPException(status_code=404, detail="ip not found")
    
    
    out.latitude = 0
    out.longitude = 0
    
    try:
        with maxminddb.open_database('data/db/dbip-city-lite-2024-11.mmdb') as reader:
            location = reader.get(ip)            
            out.ip = ip
            city = location['city']['names']['en']
            out.city = city
            if 'location' in location.keys(): 
                out.latitude = location['location']['latitude'] 
                out.longitude = location['location']['longitude']           
    except Exception as e:
        error = str(e)
        
    if error!="":
        out.error = error       
        
    return out
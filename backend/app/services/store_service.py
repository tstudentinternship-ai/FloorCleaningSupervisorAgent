from app.core.database import stores_container

def get_all_stores():
    return list(stores_container.read_all_items())

def get_store(store_id:str):
    return stores_container.read_item(
        item=store_id,
        partition_key=store_id
    )

def update_store_config(
        store_id:str,
        daily_rounds:int,
        checkpoint_count:int
):
    store=stores_container.read_item(
        item=store_id,
        partition_key=store_id
    )
    store["daily_rounds"]=daily_rounds
    store["checkpoint_count"]=checkpoint_count

    stores_container.replace_item(
        item=store_id,
        body=store
    )

    return{
        "message": "Store configuration updated"
    }
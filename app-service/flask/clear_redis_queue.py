#!/usr/bin/env python
"""
Script to clear corrupted jobs from Redis queue
Run this to fix the "time data '' does not match format" error
"""
import redis
from rq import Queue
from rq.job import Job
from rq_helpers import redis_connection

def clear_corrupted_jobs():
    """
    Clear all jobs from Redis queues to fix corruption issues
    """
    try:
        # Connect to Redis
        r = redis_connection
        
        # Get all queues
        queue = Queue('default', connection=r)
        
        print(f"Queue: {queue.name}")
        print(f"Jobs in queue: {len(queue)}")
        
        # Clear all jobs
        queue.empty()
        print("Queue cleared successfully!")
        
        # Also clear failed queue
        failed_queue = Queue('failed', connection=r)
        print(f"\nFailed queue jobs: {len(failed_queue)}")
        failed_queue.empty()
        print("Failed queue cleared!")
        
        # Clear all job-related keys
        print("\nClearing all job-related Redis keys...")
        for key in r.scan_iter("rq:job:*"):
            r.delete(key)
            print(f"Deleted: {key}")
        
        print("\n✓ All corrupted jobs cleared!")
        print("You can now restart the worker.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("Redis Queue Cleanup Script")
    print("=" * 60)
    print("\nThis will clear ALL jobs from the Redis queues.")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        clear_corrupted_jobs()
    else:
        print("Operation cancelled.")

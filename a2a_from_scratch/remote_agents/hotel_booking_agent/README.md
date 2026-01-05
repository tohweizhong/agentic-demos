# Hotel Booking Agent

This is a remote hotel booking agent that built on top of Crew AI.

Deploy to Cloud Run
```
gcloud run deploy hotel-booking-agent \
    --source remote_agents/hotel_booking_agent \
    --port=8080 \
    --allow-unauthenticated \
    --min 1 \
    --region us-central1 \
    --update-env-vars GOOGLE_CLOUD_LOCATION=us-central1 \
    --update-env-vars GOOGLE_CLOUD_PROJECT=weizhong-project03
```
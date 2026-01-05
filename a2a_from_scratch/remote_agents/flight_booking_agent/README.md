# Flight Booking Agent

This is a remote flight booking agent that built on top of LangGraph.

Deploy to Cloud Run
```
gcloud run deploy flight-booking-agent \
    --source remote_agents/flight_booking_agent \
    --port=8080 \
    --allow-unauthenticated \
    --min 1 \
    --region us-central1 \
    --update-env-vars GOOGLE_CLOUD_LOCATION=us-central1 \
    --update-env-vars GOOGLE_CLOUD_PROJECT=weizhong-project03
```

Test Docker image locally
```
gcloud auth configure-docker us-central1-docker.pkg.dev
```
```
docker pull \
    us-central1-docker.pkg.dev/weizhong-project03/cloud-run-source-deploy/flight-booking-agent:latest
```
```
PORT=8080 && docker run -p 9090:${PORT} -e PORT=${PORT} us-central1-docker.pkg.dev/weizhong-project03/cloud-run-source-deploy/flight-booking-agent:latest
```
Reference: https://docs.cloud.google.com/run/docs/testing/local
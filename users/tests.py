from django.test import TestCase

# Create your tests here.
const response = pm.response.json();

pm.environment.set(
    "refreshToken",
    response.data.refreshToken
);
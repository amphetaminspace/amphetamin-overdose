<?php
/**
 * Index file for Passenger deployment.
 * Passenger will detect this and route requests to the WSGI app.
 * The actual routing is handled by passenger_wsgi.py
 */

// Redirect to the Flask app
header("Location: /");
exit;
?>

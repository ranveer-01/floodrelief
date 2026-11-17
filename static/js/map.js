/* Optional Google Maps enhancement; the server-rendered area list always works. */
(function () {
  "use strict";
  var root = document.querySelector("[data-relief-map]");
  if (!root) return;
  var button = root.querySelector("[data-load-map]");
  var keyNode = document.getElementById("maps-browser-key");
  if (!button || !keyNode) return;
  button.hidden = false;

  button.addEventListener("click", function () {
    var message = root.querySelector("[data-map-message]");
    var canvas = root.querySelector("[data-map-canvas]");
    var rows = JSON.parse(document.getElementById("map-request-data").textContent);
    var located = rows.filter(function (row) { return row.latitude !== null && row.longitude !== null; });
    var settled = false;
    button.disabled = true;
    message.textContent = "Loading the interactive area map…";

    function unavailable() {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      canvas.hidden = true;
      message.textContent = "The interactive map is unavailable. The verified area list below remains available.";
      button.hidden = true;
    }

    var timeout = window.setTimeout(unavailable, 12000);
    window.gm_authFailure = unavailable;
    window.floodReliefMapReady = function () {
      if (settled) return;
      try {
        canvas.hidden = false;
        var map = new google.maps.Map(canvas, {
          center: { lat: located[0].latitude, lng: located[0].longitude },
          zoom: 9, streetViewControl: false, mapTypeControl: false,
        });
        var bounds = new google.maps.LatLngBounds();
        var info = new google.maps.InfoWindow();
        located.forEach(function (row) {
          var position = { lat: row.latitude, lng: row.longitude };
          bounds.extend(position);
          var marker = new google.maps.Marker({ position: position, map: map, title: row.reference + " · " + row.category });
          marker.addListener("click", function () {
            var content = document.createElement("div");
            content.className = "map-info";
            var title = document.createElement("strong");
            title.textContent = row.reference + " · " + row.category;
            var details = document.createElement("p");
            details.textContent = row.area + " · " + row.status + " · " + row.people + " people";
            var link = document.createElement("a");
            link.href = row.url;
            link.textContent = "View on the live board";
            content.append(title, details, link);
            info.setContent(content);
            info.open({ map: map, anchor: marker });
          });
        });
        if (located.length > 1) map.fitBounds(bounds);
        settled = true;
        window.clearTimeout(timeout);
        button.hidden = true;
        message.textContent = "Showing approximate areas for " + located.length + " verified requests. Use the area list for the complete details.";
      } catch (error) {
        unavailable();
      }
    };
    var url = new URL("https://maps.googleapis.com/maps/api/js");
    url.searchParams.set("key", JSON.parse(keyNode.textContent));
    url.searchParams.set("callback", "floodReliefMapReady");
    url.searchParams.set("loading", "async");
    var script = document.createElement("script");
    script.src = url.toString();
    script.async = true;
    script.onerror = unavailable;
    document.head.appendChild(script);
  }, { once: true });
})();

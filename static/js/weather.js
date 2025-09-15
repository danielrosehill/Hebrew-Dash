// Weather-specific JavaScript functions

function getWeatherIcon(code) {
  if (code === 0) return "☀️"; // Clear sky
  if (code <= 3) return "⛅"; // Mainly clear, partly cloudy
  if (code <= 48) return "☁️"; // Overcast, fog
  if (code <= 67) return "🌧️"; // Rain, freezing rain
  if (code <= 77) return "❄️"; // Snow
  if (code <= 86) return "🌦️"; // Rain showers
  if (code <= 99) return "⛈️"; // Thunderstorm
  return "❓";
}

function getWeatherDescription(code) {
  const descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
  };
  return descriptions[code] || "Unknown";
}

function formatTime(isoString) {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch (e) {
    return "--:--";
  }
}

function formatDate(isoString) {
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString([], { weekday: 'short' });
  } catch (e) {
    return "--";
  }
}

function formatHour(isoString) {
  try {
    const date = new Date(isoString);
    const hours = date.getHours();
    return `${hours}:00`;
  } catch (e) {
    return "--";
  }
}

function getWindDirection(degrees) {
  if (degrees == null) return '';
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(degrees / 22.5) % 16;
  return directions[index];
}

function getWindDirectionArrow(degrees) {
  if (degrees == null) return '';
  // Arrow pointing in wind direction (rotated from north)
  return `<span class="wind-direction-arrow" style="transform: rotate(${degrees}deg);">↓</span>`;
}

async function refreshWeather() {
  const wx = await fetchJSON('/api/weather');
  if (!wx) return;
  
  // Current weather
  if (wx.current) {
    document.getElementById('current-temp').textContent = Math.round(wx.current.temp);
    document.getElementById('current-icon').textContent = getWeatherIcon(wx.current.code);
    document.getElementById('current-desc').textContent = getWeatherDescription(wx.current.code);
    document.getElementById('feels-like').textContent = Math.round(wx.current.feels_like);
    document.getElementById('humidity').textContent = Math.round(wx.current.humidity);
    document.getElementById('wind').textContent = Math.round(wx.current.wind_speed);
    document.getElementById('wind-direction').textContent = getWindDirection(wx.current.wind_direction);
    document.getElementById('pressure').textContent = Math.round(wx.current.pressure);
  }
  
  // Today's forecast
  if (wx.today) {
    document.getElementById('today-high').textContent = Math.round(wx.today.max);
    document.getElementById('today-low').textContent = Math.round(wx.today.min);
    document.getElementById('today-icon').textContent = getWeatherIcon(wx.today.code);
    document.getElementById('uv-index').textContent = wx.today.uv_index || '--';
    document.getElementById('precipitation').textContent = wx.today.precipitation || '0';
    
    // Format sunrise/sunset times
    if (wx.today.sunrise) {
      document.getElementById('sunrise').textContent = formatTime(wx.today.sunrise);
    }
    if (wx.today.sunset) {
      document.getElementById('sunset').textContent = formatTime(wx.today.sunset);
    }
  }
  
  // Tomorrow's forecast
  if (wx.forecast && wx.forecast.length > 1) {
    const tomorrow = wx.forecast[1]; // Second day in forecast is tomorrow
    document.getElementById('tomorrow-high').textContent = Math.round(tomorrow.max);
    document.getElementById('tomorrow-low').textContent = Math.round(tomorrow.min);
    document.getElementById('tomorrow-icon').textContent = getWeatherIcon(tomorrow.code);
    document.getElementById('tomorrow-uv-index').textContent = tomorrow.uv_index || '--';
    document.getElementById('tomorrow-precipitation').textContent = tomorrow.precipitation || '0';
    
    // Format sunrise/sunset times for tomorrow
    if (tomorrow.sunrise) {
      document.getElementById('tomorrow-sunrise').textContent = formatTime(tomorrow.sunrise);
    }
    if (tomorrow.sunset) {
      document.getElementById('tomorrow-sunset').textContent = formatTime(tomorrow.sunset);
    }
  }
  
  // 7-day forecast
  const forecastContainer = document.getElementById('forecast-container');
  forecastContainer.innerHTML = '';
  if (wx.forecast && wx.forecast.length > 0) {
    wx.forecast.forEach(day => {
      const dayElement = document.createElement('div');
      dayElement.className = 'forecast-day';
      
      const date = new Date(day.date);
      const today = new Date();
      const isToday = date.getDate() === today.getDate() && date.getMonth() === today.getMonth();
      
      dayElement.innerHTML = `
        <div class="forecast-day-header">${isToday ? 'Today' : date.toLocaleDateString([], { weekday: 'short' })}</div>
        <div class="forecast-day-icon">${getWeatherIcon(day.code)}</div>
        <div class="forecast-day-temp">${Math.round(day.max)}°</div>
        <div class="forecast-day-temp" style="color: var(--muted);">${Math.round(day.min)}°</div>
      `;
      
      forecastContainer.appendChild(dayElement);
    });
  }
  
  // Store hourly data globally for toggle functionality
  window.weatherData = wx;
  
  // Initialize hourly forecasts for both days
  displayHourlyForecast('today', 'today-hourly-container');
  displayHourlyForecast('tomorrow', 'tomorrow-hourly-container');
  
  // Air quality (reuse existing functionality)
  const aq = await fetchJSON('/api/aqi');
  if (aq) {
    if (aq.pm25 != null) {
      document.getElementById('pm25').textContent = Math.round(aq.pm25);
      setPm25Badge(document.getElementById('pm25-desc'), aq.pm25);
    }
    if (aq.aqi != null) {
      document.getElementById('aqi').textContent = Math.round(aq.aqi);
      setAqiBadge(document.getElementById('aqi-desc'), aq.aqi);
    }
  }
}

function displayHourlyForecast(day, containerId) {
  const hourlyContainer = document.getElementById(containerId);
  hourlyContainer.innerHTML = '';
  
  if (!window.weatherData || !window.weatherData.hourly || window.weatherData.hourly.length === 0) {
    return;
  }
  
  const now = new Date();
  const targetDate = day === 'today' ? now : new Date(now.getTime() + 24 * 60 * 60 * 1000);
  const targetDay = targetDate.getDate();
  const targetMonth = targetDate.getMonth();
  
  // Filter hourly data for the selected day
  const dayHours = window.weatherData.hourly.filter(hour => {
    const hourDate = new Date(hour.time);
    return hourDate.getDate() === targetDay && hourDate.getMonth() === targetMonth;
  });
  
  // For today, show only future hours
  const filteredHours = day === 'today' 
    ? dayHours.filter(hour => new Date(hour.time) >= now)
    : dayHours;
  
  // Limit to next 24 hours
  const displayHours = filteredHours.slice(0, 24);
  
  displayHours.forEach(hour => {
    const hourElement = document.createElement('div');
    const precipitationPercent = Math.round((hour.precipitation || 0) * 10); // Convert mm to rough percentage
    const isHighPrecipitation = precipitationPercent > 50;
    
    hourElement.className = `hourly-item${isHighPrecipitation ? ' high-precipitation' : ''}`;
    
    hourElement.innerHTML = `
      <div class="hourly-time">${formatHour(hour.time)}</div>
      <div class="hourly-icon">${getWeatherIcon(hour.code)}</div>
      <div class="hourly-temp">${Math.round(hour.temp)}°</div>
      <div class="hourly-precipitation${isHighPrecipitation ? ' high' : ''}">${precipitationPercent}%</div>
    `;
    
    hourlyContainer.appendChild(hourElement);
  });
}

function switchWeatherTab(activeTab) {
  // Remove active class from all tabs
  document.querySelectorAll('.weather-tab').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Remove active class from all tab contents
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });
  
  // Add active class to selected tab and content
  document.getElementById(`${activeTab}-tab`).classList.add('active');
  document.getElementById(`${activeTab}-content`).classList.add('active');
}

// Initialize weather refresh
document.addEventListener('DOMContentLoaded', () => {
  refreshWeather();
  setInterval(refreshWeather, 5 * 60 * 1000); // Refresh every 5 minutes
  
  // Add tab event listeners
  document.getElementById('today-tab').addEventListener('click', () => {
    switchWeatherTab('today');
  });
  
  document.getElementById('tomorrow-tab').addEventListener('click', () => {
    switchWeatherTab('tomorrow');
  });
  
  document.getElementById('forecast-tab').addEventListener('click', () => {
    switchWeatherTab('forecast');
  });
});
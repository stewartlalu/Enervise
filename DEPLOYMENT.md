# Enervise - Energy Meter Reading System

A Flask-based web application for automated meter reading using Roboflow AI and real-time bill calculation.

## 🚀 Features

- **AI-Powered Meter Reading**: Uses trained Roboflow model for accurate digit detection
- **Real-time Bill Calculation**: Automatic bill calculation using Selenium web scraping
- **Video Processing**: Processes video files for meter reading detection
- **User Authentication**: Secure login system with Flask-Login
- **Dashboard Analytics**: Comprehensive dashboard with charts and analytics
- **Alert System**: Cost limit alerts and notifications
- **Responsive Design**: Modern UI with Legal CRM theme

## 📁 Project Structure

```
├── app.py                 # Main Flask application
├── database.py            # Database operations
├── roboflow_integration.py # Roboflow API integration
├── templates/             # HTML templates
│   ├── index.html         # Camera feed page
│   ├── dashboard.html     # Dashboard page
│   ├── profile.html       # Profile page
│   ├── alerts.html        # Alerts page
│   └── Login.html         # Login page
├── static/                # Static files
│   └── sample.mp4         # Sample video file
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
└── README.md             # This file
```

## 🛠️ Installation & Setup

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd enervise
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open http://localhost:5000
   - Login with: email: `admin@example.com`, password: `admin123`

## 🌐 Vercel Deployment

### Prerequisites

1. **GitHub Repository**: Push your code to GitHub
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
3. **Environment Variables**: Set up in Vercel dashboard

### Deployment Steps

1. **Connect GitHub to Vercel**
   - Go to Vercel dashboard
   - Click "New Project"
   - Import your GitHub repository

2. **Configure Environment Variables**
   In Vercel dashboard, add these environment variables:
   ```
   ROBOFLOW_API_KEY=your_actual_api_key
   ROBOFLOW_PROJECT_ID=your_project_id
   ROBOFLOW_MODEL_VERSION=your_model_version
   FLASK_SECRET_KEY=your_secret_key
   ```

3. **Deploy**
   - Vercel will automatically deploy your application
   - Your app will be available at `https://your-project.vercel.app`

### Vercel Configuration

The `vercel.json` file is already configured for:
- Python 3.9 runtime
- Flask application
- 30-second timeout for functions
- Automatic routing

## 🔧 Configuration

### Roboflow API Setup

1. **Get API Key**: From your Roboflow account
2. **Project Details**: 
   - Project ID: `7-segments-custom-hblhp`
   - Model Version: `6`
   - Confidence: `0.05`

### Database

- **SQLite**: Used for local development
- **Automatic Setup**: Database tables are created on first run
- **Data Persistence**: Readings and user settings are stored

## 📱 Usage

### Camera Feed Page
1. **Select Meter Type**: Single Phase or Three Phase
2. **Start Process**: Begin video playback and detection
3. **Monitor Readings**: Real-time meter reading detection
4. **Stop Process**: Pause detection and video

### Dashboard Page
1. **View Analytics**: Charts and consumption data
2. **Set Daily Limit**: Configure cost limits
3. **Monitor Usage**: Track daily consumption

### Profile Page
1. **Edit Profile**: Update user information
2. **Manage Settings**: Configure preferences

### Alerts Page
1. **View Notifications**: See all alerts
2. **Manage Alerts**: Configure alert settings

## 🔒 Security Features

- **User Authentication**: Flask-Login integration
- **Session Management**: Secure session handling
- **Input Validation**: Form validation and sanitization
- **CSRF Protection**: Built-in Flask security

## 🐛 Troubleshooting

### Common Issues

1. **ChromeDriver Issues**
   - WebDriver Manager handles automatic driver updates
   - For Vercel: Chrome is pre-installed

2. **Roboflow API Errors**
   - Check API key validity
   - Verify project ID and model version
   - Check internet connectivity

3. **Database Issues**
   - Database is created automatically
   - Clear browser cache if issues persist

### Debug Mode

Enable debug mode for development:
```python
app.run(debug=True)
```

## 📊 API Endpoints

- `GET /` - Redirects to login
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /camera` - Camera feed page
- `GET /dashboard` - Dashboard page
- `GET /profile` - Profile page
- `GET /alerts` - Alerts page
- `POST /start_process` - Start meter reading
- `POST /stop_process` - Stop meter reading
- `POST /process_meter_reading` - Process reading
- `GET /get_readings` - Get reading history
- `POST /clear_all` - Clear all readings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting section

## 🔄 Updates

### Version 1.0.0
- Initial release
- AI-powered meter reading
- Real-time bill calculation
- User authentication
- Dashboard analytics
- Vercel deployment ready

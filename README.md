# Enervise - AI-Powered Energy Meter Reading System

A modern Flask-based web application that uses **Roboflow AI** for automated meter reading detection and real-time bill calculation. Features a beautiful Legal CRM-themed UI with comprehensive dashboard analytics.


## ✨ Key Features

### 🤖 AI-Powered Meter Reading
- **Roboflow Integration**: Uses trained AI model for accurate digit detection
- **Video Processing**: Processes video files for meter reading detection
- **Real-time Detection**: 5-second interval detection with duplicate prevention
- **Confidence-based**: Adjustable confidence thresholds for optimal accuracy

### 💰 Smart Bill Calculation
- **Automated Billing**: Real-time bill calculation using Selenium web scraping
- **Multi-phase Support**: Single-phase and three-phase meter support
- **Cost Tracking**: Daily cost limits with visual progress indicators
- **Alert System**: Notifications for approaching or exceeding limits

### 📊 Comprehensive Dashboard
- **Real-time Analytics**: Live consumption monitoring and trends
- **Interactive Charts**: Chart.js powered visualizations
- **Cost Management**: Set and monitor daily spending limits
- **Historical Data**: Complete reading history with timestamps

### 🔐 Secure Authentication
- **Flask-Login**: Secure user authentication system
- **Session Management**: Protected routes and session handling
- **User Profiles**: Editable user profiles and settings

### 🎨 Modern UI/UX
- **Legal CRM Theme**: Professional, modern design
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Live data updates without page refresh
- **Toast Notifications**: User-friendly feedback system

## 🛠️ Tech Stack

- **Backend**: Python Flask
- **AI/ML**: Roboflow API for meter reading detection
- **Database**: SQLite3 with automatic setup
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Charts**: Chart.js for data visualization
- **Web Scraping**: Selenium with WebDriver Manager
- **Deployment**: Vercel-ready configuration

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/enervise.git
   cd enervise
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your Roboflow API credentials
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open http://localhost:5000
   - Login: `admin@example.com` / `admin123`

### Vercel Deployment

1. **Fork this repository**
2. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Add environment variables in Vercel dashboard

3. **Deploy**
   - Vercel automatically deploys your application
   - Access at `https://your-project.vercel.app`

## 📁 Project Structure

```
enervise/
├── app.py                    # Main Flask application
├── database.py               # Database operations
├── roboflow_integration.py   # Roboflow API integration
├── templates/                # HTML templates
│   ├── index.html           # Camera feed page
│   ├── dashboard.html       # Dashboard analytics
│   ├── profile.html         # User profile
│   ├── alerts.html          # Alert management
│   └── Login.html           # Authentication
├── static/                   # Static assets
│   └── sample.mp4           # Sample video file
├── requirements.txt          # Python dependencies
├── vercel.json              # Vercel deployment config
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🔧 Configuration

### Roboflow API Setup
- **API Key**: Get from your Roboflow account
- **Project ID**: `7-segments-custom-hblhp`
- **Model Version**: `6`
- **Confidence**: `0.05` (optimized for speed)

### Environment Variables
```bash
ROBOFLOW_API_KEY=your_api_key_here
ROBOFLOW_PROJECT_ID=your_project_id
ROBOFLOW_MODEL_VERSION=your_model_version
FLASK_SECRET_KEY=your_secret_key
```

## 📱 Usage Guide

### Camera Feed Page
1. **Select Meter Type**: Choose Single Phase or Three Phase
2. **Start Process**: Begin video playback and AI detection
3. **Monitor Readings**: Watch real-time meter reading detection
4. **Stop Process**: Pause detection when needed

### Dashboard Page
1. **View Analytics**: Comprehensive consumption charts
2. **Set Daily Limit**: Configure spending limits
3. **Monitor Usage**: Track daily consumption patterns

### Profile Page
1. **Edit Profile**: Update user information
2. **Manage Settings**: Configure preferences

## 🔒 Security Features

- **User Authentication**: Flask-Login integration
- **Session Management**: Secure session handling
- **Input Validation**: Form validation and sanitization
- **CSRF Protection**: Built-in Flask security
- **Environment Variables**: Secure credential management

## 🐛 Troubleshooting

### Common Issues
1. **ChromeDriver**: WebDriver Manager handles automatic updates
2. **Roboflow API**: Check API key and internet connectivity
3. **Database**: Automatically created on first run
4. **Vercel Deployment**: Ensure environment variables are set

### Debug Mode
```python
app.run(debug=True)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Roboflow**: For AI-powered meter reading detection
- **Flask**: For the excellent web framework
- **Chart.js**: For beautiful data visualizations
- **Vercel**: For seamless deployment platform

## 📞 Support

- 📧 Email: support@enervise.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/enervise/issues)
- 📖 Documentation: [Full Documentation](DEPLOYMENT.md)

---

**Made with ❤️ for efficient energy management**

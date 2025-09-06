# Real-Time Exam Monitoring System

A comprehensive Spring Boot application that provides AI-powered real-time monitoring for online exams to detect and prevent cheating behaviors.

## Features

### 🎯 Core Monitoring Capabilities
- **Face Detection & Tracking**: Real-time detection of student presence and attention
- **Behavior Analysis**: Detection of looking away, multiple people, no face, and screen blur
- **Tab Switching Detection**: Monitors browser tab changes and focus loss
- **Real-time Alerts**: Immediate voice and visual warnings for suspicious behavior
- **Comprehensive Logging**: Detailed tracking of all student activities during exams

### 🏗️ System Architecture
- **Backend**: Spring Boot 3.2.0 with Spring Security
- **Database**: PostgreSQL with JPA/Hibernate
- **Computer Vision**: OpenCV for real-time image analysis
- **Frontend**: Thymeleaf templates with JavaScript monitoring
- **Security**: BCrypt password encryption and session management

### 📊 Admin Features
- **Exam Management**: Create, manage, and monitor exam sessions
- **Student Dashboard**: Real-time monitoring of all students
- **Behavior Analytics**: Detailed reports and statistics
- **Session Control**: Start/stop exam sessions remotely

### 👨‍🎓 Student Features
- **Exam Interface**: Clean, distraction-free exam environment
- **Real-time Feedback**: Immediate alerts for rule violations
- **Progress Tracking**: View personal statistics and history
- **Secure Authentication**: Role-based access control

## Prerequisites

- Java 17 or higher
- Maven 3.6+
- PostgreSQL 12+
- Webcam-enabled device
- Modern web browser with camera support

## Installation & Setup

### 1. Database Setup

```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE exam_monitoring;"

# Run the setup script
psql -U postgres -d exam_monitoring -f database_setup.sql
```

### 2. Application Configuration

Update `src/main/resources/application.yml` with your database credentials:

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/exam_monitoring
    username: your_username
    password: your_password
```

### 3. Build and Run

```bash
# Clone the repository
git clone <repository-url>
cd exam-monitoring-system

# Build the application
mvn clean install

# Run the application
mvn spring-boot:run
```

The application will be available at `http://localhost:8080`

## Default Credentials

- **Admin**: `admin` / `admin123`
- **Student 1**: `student1` / `password1`
- **Student 2**: `student2` / `password2`

## Usage Guide

### For Administrators

1. **Login** with admin credentials
2. **Create Exams** using the exam management interface
3. **Start Exam Sessions** to make exams available to students
4. **Monitor Students** in real-time through the admin dashboard
5. **Review Reports** and behavior analytics

### For Students

1. **Login** with student credentials
2. **View Available Exams** from the student dashboard
3. **Start Exam** and allow camera access when prompted
4. **Take Exam** while being monitored for suspicious behavior
5. **Receive Alerts** if any rule violations are detected

## Technical Details

### Monitoring Detection Types

- **Looking Away**: Detects when student looks away from screen
- **Multiple People**: Identifies presence of additional people in frame
- **No Face**: Detects when student is not visible in camera
- **Screen Blur**: Identifies blurry or unclear camera feed
- **Tab Switching**: Monitors browser tab changes and focus loss

### Security Features

- **Password Encryption**: BCrypt hashing for secure password storage
- **Session Management**: Secure session handling with timeout
- **Role-based Access**: Separate interfaces for students and administrators
- **Data Privacy**: No video recording, only event logging

### Performance Optimizations

- **Efficient Image Processing**: Optimized OpenCV operations
- **Alert Cooldowns**: Prevents spam alerts with intelligent timing
- **Database Indexing**: Optimized queries for fast data retrieval
- **Caching**: Strategic caching for improved performance

## API Endpoints

### Authentication
- `POST /login` - User authentication
- `GET /logout` - User logout

### Detection
- `POST /api/detection/analyze` - Analyze webcam frame
- `POST /api/detection/tab_switch` - Report tab switching
- `GET /api/detection/history/{username}` - Get detection history

### Exam Management
- `GET /admin/exams` - List all exams
- `POST /admin/create_exam` - Create new exam
- `POST /admin/start_exam/{examId}` - Start exam session
- `POST /admin/stop_exam/{sessionId}` - Stop exam session

### Student Interface
- `GET /student/exams` - View available exams
- `GET /student/start_exam/{sessionId}` - Start specific exam
- `POST /student/submit_answer` - Submit exam answer

## Configuration

### Application Properties

```yaml
app:
  monitoring:
    alert-cooldown-seconds: 5
    face-detection-threshold: 15.0
    blur-detection-threshold: 15.0
```

### Database Configuration

The application uses JPA with Hibernate for database operations. Tables are automatically created on startup with `ddl-auto: create-drop`.

## Troubleshooting

### Common Issues

1. **Camera Access Denied**
   - Ensure browser has camera permissions
   - Check if camera is being used by another application

2. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check database credentials in application.yml

3. **OpenCV Loading Errors**
   - Ensure OpenCV dependencies are properly installed
   - Check if classifier files are in the classpath

### Performance Issues

- **High CPU Usage**: Reduce monitoring frequency in JavaScript
- **Memory Issues**: Increase JVM heap size
- **Database Slowdown**: Check database indexes and query optimization

## Development

### Project Structure

```
src/
├── main/
│   ├── java/com/exammonitoring/
│   │   ├── config/          # Configuration classes
│   │   ├── controller/      # REST controllers
│   │   ├── entity/          # JPA entities
│   │   ├── repository/      # Data access layer
│   │   ├── service/         # Business logic
│   │   └── ExamMonitoringApplication.java
│   └── resources/
│       ├── static/js/       # JavaScript files
│       ├── templates/       # Thymeleaf templates
│       └── application.yml  # Configuration
```

### Adding New Detection Types

1. Add new enum value to `DetectionType`
2. Update `ComputerVisionService` analysis logic
3. Add corresponding database fields
4. Update frontend JavaScript handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support or questions:
- Create an issue in the repository
- Contact the development team
- Check the troubleshooting section

## Acknowledgments

- OpenCV for computer vision capabilities
- Spring Boot for the robust backend framework
- PostgreSQL for reliable data storage
- All contributors and testers

---

**Note**: This system is designed for educational purposes and should be used in compliance with privacy laws and institutional policies. Always inform students about monitoring and obtain necessary consents.

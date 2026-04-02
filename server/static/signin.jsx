import "./signin.css";
import { FcGoogle } from "react-icons/fc";
import { FaFacebook } from "react-icons/fa";

function Cube() {
  return (
    <svg className="svg-cube" width="220" height="220" viewBox="0 0 100 100">
      <polygon points="50,5 95,28 50,50 5,28"  fill="#6b8fff"/>
      <polygon points="5,28 50,50 50,95 5,72"   fill="#3a50d9"/>
      <polygon points="95,28 50,50 50,95 95,72" fill="#2a3fc0"/>
    </svg>
  );
}


function Capsule() {
  return (
    <svg className="svg-capsule" width="130" height="130" viewBox="0 0 60 96">
      <rect x="10" y="10" width="40" height="76" rx="20" ry="20" fill="#1a1a1a"/>
    </svg>
  );
}

function Flower() {
  return (
    <svg className="svg-flower" width="120" height="120" viewBox="0 0 80 80">
      <ellipse cx="40" cy="22" rx="12" ry="18" fill="#c0c8d8" opacity="0.8"/>
      <ellipse cx="58" cy="40" rx="18" ry="12" fill="#c0c8d8" opacity="0.8"/>
      <ellipse cx="40" cy="58" rx="12" ry="18" fill="#c0c8d8" opacity="0.8"/>
      <ellipse cx="22" cy="40" rx="18" ry="12" fill="#c0c8d8" opacity="0.8"/>
      <circle cx="40" cy="40" r="10" fill="#b0b8cc"/>
    </svg>
  );
}

export default function SignIn() {
  return (
    <div className="wrapper">

      {/* Floating Shapes */}
      <div className="shape-cube"><Cube /></div>
      <div className="shape-capsule"><Capsule /></div>
      <div className="shape-flower"><Flower /></div>

      {/* Glass Card */}
      <div className="card">
        <div className="card-grid">

          {/* Left part */}
          <div>
            <h1 className="title">Log In</h1>
            <p className="subtitle">Welcome back! Please enter your details.</p>
            <div className="fields">
              <input className="input-field" type="email"    placeholder="Email Address"/>
              <input className="input-field" type="password" placeholder="Password"/>
              <a href="#" className="forgot">Forgot password?</a>
            </div>
          </div>

          {/* Right part */}
          <div className="right-col">
            <button className="btn-primary">Log In</button>
            <p className="login-text">
              Don't have an account? <a href="#">Sign Up</a>
            </p>
            <p className="or-text">Or</p>
            <button className="btn-social"><FcGoogle size={20}/> Continue with Google</button>
            <button className="btn-social"><FaFacebook size={20} color="#1877F2"/> Continue with Facebook</button>
          </div>

        </div>
      </div>

    </div>
  );
}

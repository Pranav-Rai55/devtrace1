@import "tailwindcss";

html,
body,
#root {
  min-height: 100%;
  background-color: #020204;
}
@keyframes floatSlow {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-15px);
  }
}

.animate-floatSlow {
  animation: floatSlow 5s ease-in-out infinite;
}
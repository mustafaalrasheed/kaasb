import Link from "next/link";

export default function HomePage() {
  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-brand-500 via-brand-600 to-brand-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <div className="max-w-3xl">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
              Find the perfect
              <span className="text-brand-200"> freelancer </span>
              for your project
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-blue-100 leading-relaxed">
              Kaasb connects businesses with talented freelancers worldwide.
              Post a job, review proposals, and hire the best — all in one place.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row gap-4">
              <Link
                href="/auth/register"
                className="btn-primary bg-white text-brand-600 hover:bg-blue-50 text-center text-lg px-8 py-3"
              >
                Get Started Free
              </Link>
              <Link
                href="/jobs"
                className="btn-secondary border-white/30 text-white hover:bg-white/10 text-center text-lg px-8 py-3"
              >
                Browse Jobs
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900">
            How Kaasb Works
          </h2>
          <p className="mt-4 text-center text-gray-600 max-w-2xl mx-auto">
            Getting started is simple. Whether you&apos;re hiring or freelancing,
            Kaasb makes it easy.
          </p>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Post a Job",
                description:
                  "Describe your project, set your budget, and post it to thousands of freelancers.",
                icon: "📝",
              },
              {
                step: "02",
                title: "Review Proposals",
                description:
                  "Receive proposals from qualified freelancers. Compare skills, rates, and reviews.",
                icon: "🔍",
              },
              {
                step: "03",
                title: "Hire & Collaborate",
                description:
                  "Choose the best fit, collaborate through our platform, and pay securely.",
                icon: "🤝",
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="text-5xl mb-4">{item.icon}</div>
                <div className="text-sm font-bold text-brand-500 mb-2">
                  STEP {item.step}
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {item.title}
                </h3>
                <p className="mt-3 text-gray-600">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold text-gray-900">
            Ready to get started?
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Join thousands of freelancers and businesses on Kaasb.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link href="/auth/register" className="btn-primary text-lg px-8 py-3">
              Sign Up as Freelancer
            </Link>
            <Link
              href="/auth/register"
              className="btn-secondary text-lg px-8 py-3"
            >
              Hire a Freelancer
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="text-2xl font-bold text-white">Kaasb</div>
            <p className="mt-4 md:mt-0 text-sm">
              &copy; {new Date().getFullYear()} Kaasb. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

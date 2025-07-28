export default function AboutPage() {
  return (
    <main className="min-h-screen bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 px-4 sm:px-6 lg:px-8 py-16">
      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl font-bold mb-6">About Us</h1>
        <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-300 mb-8">
          Welcome to <span className="font-semibold text-blue-600 dark:text-blue-400">MySite</span> — where innovation meets simplicity. 
        </p>
        <div className="mt-12 grid sm:grid-cols-2 gap-8 text-left">
          <div>
            <h2 className="text-xl font-semibold mb-2">Our Mission</h2>
            <p className="text-gray-700 dark:text-gray-300">
              To empower individuals and businesses through thoughtfully designed tools that solve real-world problems.
            </p>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">What We Do</h2>
            <p className="text-gray-700 dark:text-gray-300">
              From web apps to APIs and design systems, we build fast, accessible, and scalable solutions tailored to our users.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}

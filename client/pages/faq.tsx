import React from 'react';
import Navbar from '@/components/navbar';
import Footer from '@/components/Footer';

export default function FAQ() {
  const faqs = [
    {
      question: 'What is IPO Street?',
      answer: 'IPO Street is a platform that helps you track upcoming Initial Public Offerings (IPOs). We provide real-time data on companies planning to go public, including share prices, offering dates, and company information.',
    },
    {
      question: 'How do I add IPOs to my watchlist?',
      answer: 'Simply create a free account, then click the star icon next to any IPO you want to track. You can view all your saved IPOs on your Watchlist page.',
    },
    {
      question: 'Is IPO Street free to use?',
      answer: 'Yes! IPO Street is completely free. You can browse upcoming IPOs, create a watchlist, and access all our features at no cost.',
    },
    {
      question: 'How often is the IPO data updated?',
      answer: 'Our IPO data is updated regularly to ensure you have the most current information about upcoming offerings.',
    },
    {
      question: 'What information do you provide for each IPO?',
      answer: 'For each IPO, we provide the company name, ticker symbol, exchange, shares offered, estimated share price, IPO date, latest filing type, and estimated market cap.',
    },
    {
      question: 'Can I invest directly through IPO Street?',
      answer: 'No, IPO Street is an information platform only. We provide data to help you research IPOs, but you\'ll need to use a brokerage account to invest.',
    },
    {
      question: 'How do I delete my account?',
      answer: 'Account deletion is coming soon. For now, you can simply stop using the service and your watchlist data will remain private.',
    },
    {
      question: 'Do you offer investment advice?',
      answer: 'No, IPO Street provides information only and does not offer investment advice. Always consult with a financial advisor before making investment decisions.',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          Frequently Asked Questions
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mb-12">
          Find answers to common questions about IPO Street
        </p>

        <div className="space-y-6">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700"
            >
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                {faq.question}
              </h2>
              <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                {faq.answer}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-12 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Still have questions?
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            We&apos;re constantly updating our FAQ section. Check back soon for more answers!
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}

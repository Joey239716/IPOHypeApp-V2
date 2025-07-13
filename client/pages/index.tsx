/* import React, { useEffect, useState } from 'react'


function index() {

  const [message, setMessage] = useState("Loading");
  const [people, setPeople] = useState([])

  useEffect(() => {
    fetch("http://localhost:8080/api/home")
    .then((response) => response.json())
    .then((data) => {
      setMessage(data.message);
      setPeople(data.people);
      console.log(data.people)
    });
  }, []);

  return (
    <div>
      <div>{message}</div>
      <div>
      {
        people.map((person, index) => (
          <div key = {index}>
            {person}
          </div>
        ))
      }
      </div>
    </div>
  )
}

export default index
*/

import Navbar from '@/components/navbar'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        {children}
      </body>
    </html>
  )
}
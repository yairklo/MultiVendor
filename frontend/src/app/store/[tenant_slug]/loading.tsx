import React from 'react'

export default function StoreLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8">
      <div className="text-center space-y-4">
        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" role="status">
          <span className="!absolute !-m-px !h-px !w-px !overflow-hidden !whitespace-nowrap !border-0 !p-0 ![clip:rect(0,0,0,0)]">
            Loading...
          </span>
        </div>
        <p className="text-gray-500 font-medium animate-pulse">Loading store...</p>
      </div>
    </div>
  )
}

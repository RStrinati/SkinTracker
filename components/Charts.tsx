'use client';

import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ChartsProps {
  productData: { date: string; count: number }[];
  triggerData: { date: string; count: number }[];
  symptomData: { date: string; severity: number }[];
}

export default function Charts({ productData, triggerData, symptomData }: ChartsProps) {
  return (
    <>
      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={productData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="count" name="Product usage" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={triggerData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="count" name="Trigger frequency" stroke="#82ca9d" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={symptomData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 5]} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="severity" name="Symptom severity" stroke="#ff7300" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
